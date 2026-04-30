from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlmodel import Session, desc, select

from app.config import get_settings
from app.database import get_session
from app.models import Exercise, FeedbackReport, PracticeSession, Recording, SessionStatus, User
from app.schemas import (
    FeedbackReportRead,
    PracticeSessionCreate,
    PracticeSessionRead,
    RecordingUploadRead,
)
from app.services.analyzer import analyze_recording

router = APIRouter(prefix="/practice-sessions", tags=["practice sessions"])


@router.post("", response_model=PracticeSessionRead, status_code=status.HTTP_201_CREATED)
def create_practice_session(
    payload: PracticeSessionCreate, session: Session = Depends(get_session)
) -> PracticeSession:
    user = session.get(User, payload.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    exercise = session.get(Exercise, payload.exercise_id)
    if exercise is None or exercise.user_id != payload.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    practice_session = PracticeSession(user_id=payload.user_id, exercise_id=payload.exercise_id)
    session.add(practice_session)
    session.commit()
    session.refresh(practice_session)
    return practice_session


@router.get("/{practice_session_id}", response_model=PracticeSessionRead)
def get_practice_session(
    practice_session_id: int, session: Session = Depends(get_session)
) -> PracticeSession:
    practice_session = session.get(PracticeSession, practice_session_id)
    if practice_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found"
        )
    return practice_session


@router.post("/{practice_session_id}/recordings", response_model=RecordingUploadRead)
async def upload_recording(
    practice_session_id: int,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> RecordingUploadRead:
    practice_session = session.get(PracticeSession, practice_session_id)
    if practice_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found"
        )

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    suffix = Path(file.filename or "recording.wav").suffix or ".wav"
    stored_name = f"{practice_session_id}-{uuid4().hex}{suffix}"
    file_path = upload_dir / stored_name
    file_path.write_bytes(await file.read())

    recording = Recording(
        practice_session_id=practice_session_id,
        original_filename=file.filename or stored_name,
        file_path=str(file_path),
        content_type=file.content_type or "application/octet-stream",
    )
    practice_session.status = SessionStatus.recording_uploaded
    session.add(recording)
    session.add(practice_session)
    session.commit()
    session.refresh(recording)

    feedback_report = analyze_recording(session, recording)
    session.refresh(recording)

    return RecordingUploadRead(recording=recording, feedback_report=feedback_report)


@router.get("/{practice_session_id}/feedback", response_model=list[FeedbackReportRead])
def get_feedback_reports(
    practice_session_id: int, session: Session = Depends(get_session)
) -> list[FeedbackReport]:
    practice_session = session.get(PracticeSession, practice_session_id)
    if practice_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found"
        )

    return session.exec(
        select(FeedbackReport).where(FeedbackReport.practice_session_id == practice_session_id)
    ).all()


@router.get("/{practice_session_id}/feedback/latest", response_model=FeedbackReportRead)
def get_latest_feedback_report(
    practice_session_id: int, session: Session = Depends(get_session)
) -> FeedbackReport:
    practice_session = session.get(PracticeSession, practice_session_id)
    if practice_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found"
        )

    feedback_report = session.exec(
        select(FeedbackReport)
        .where(FeedbackReport.practice_session_id == practice_session_id)
        .order_by(desc(FeedbackReport.created_at))
    ).first()
    if feedback_report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Feedback not found")

    return feedback_report
