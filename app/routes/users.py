from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, desc, select

from app.database import get_session
from app.models import Exercise, FeedbackReport, PracticeSession, Recording, User, UserPreference
from app.schemas import (
    FeedbackReportRead,
    PracticeSessionSummaryRead,
    PracticeStatsRead,
    PreferenceRead,
    PreferenceUpsert,
    UserCreate,
    UserRead,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, session: Session = Depends(get_session)) -> User:
    user = User(display_name=payload.display_name, email=payload.email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, session: Session = Depends(get_session)) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}/preferences", response_model=PreferenceRead)
def upsert_preferences(
    user_id: int, payload: PreferenceUpsert, session: Session = Depends(get_session)
) -> UserPreference:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    preference = session.exec(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).first()
    if preference is None:
        preference = UserPreference(user_id=user_id, **payload.model_dump())
    else:
        for key, value in payload.model_dump().items():
            setattr(preference, key, value)
        preference.updated_at = datetime.now(UTC)

    session.add(preference)
    session.commit()
    session.refresh(preference)
    return preference


@router.get("/{user_id}/preferences", response_model=PreferenceRead)
def get_preferences(user_id: int, session: Session = Depends(get_session)) -> UserPreference:
    preference = session.exec(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).first()
    if preference is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Preferences not found")
    return preference


@router.get("/{user_id}/practice-sessions", response_model=list[PracticeSessionSummaryRead])
def get_user_practice_sessions(
    user_id: int,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[PracticeSessionSummaryRead]:
    ensure_user_exists(user_id, session)
    practice_sessions = session.exec(
        select(PracticeSession)
        .where(PracticeSession.user_id == user_id)
        .order_by(desc(PracticeSession.started_at))
        .limit(limit)
    ).all()

    summaries = []
    for practice_session in practice_sessions:
        exercise = session.get(Exercise, practice_session.exercise_id)
        latest_feedback = get_latest_feedback_for_session(practice_session.id, session)
        summaries.append(
            PracticeSessionSummaryRead(
                id=practice_session.id,
                exercise_id=practice_session.exercise_id,
                exercise_title=exercise.title if exercise else "Unknown exercise",
                status=practice_session.status,
                started_at=practice_session.started_at,
                completed_at=practice_session.completed_at,
                latest_score=latest_feedback.score if latest_feedback else None,
                latest_summary=latest_feedback.summary if latest_feedback else None,
            )
        )

    return summaries


@router.get("/{user_id}/feedback-reports", response_model=list[FeedbackReportRead])
def get_user_feedback_reports(
    user_id: int,
    limit: int = 20,
    session: Session = Depends(get_session),
) -> list[FeedbackReport]:
    ensure_user_exists(user_id, session)
    practice_session_ids = session.exec(
        select(PracticeSession.id).where(PracticeSession.user_id == user_id)
    ).all()
    if not practice_session_ids:
        return []

    return session.exec(
        select(FeedbackReport)
        .where(FeedbackReport.practice_session_id.in_(practice_session_ids))
        .order_by(desc(FeedbackReport.created_at))
        .limit(limit)
    ).all()


@router.get("/{user_id}/practice-stats", response_model=PracticeStatsRead)
def get_user_practice_stats(
    user_id: int,
    session: Session = Depends(get_session),
) -> PracticeStatsRead:
    ensure_user_exists(user_id, session)
    practice_sessions = session.exec(
        select(PracticeSession).where(PracticeSession.user_id == user_id)
    ).all()
    practice_session_ids = [practice_session.id for practice_session in practice_sessions]
    feedback_reports = []
    if practice_session_ids:
        feedback_reports = session.exec(
            select(FeedbackReport).where(FeedbackReport.practice_session_id.in_(practice_session_ids))
        ).all()

    scores = [report.score for report in feedback_reports]
    recordings = []
    if practice_session_ids:
        recordings = session.exec(
            select(Recording).where(Recording.practice_session_id.in_(practice_session_ids))
        ).all()

    return PracticeStatsRead(
        user_id=user_id,
        total_sessions=len(practice_sessions),
        completed_sessions=sum(
            1 for practice_session in practice_sessions if practice_session.completed_at is not None
        ),
        total_recordings=len(recordings),
        total_feedback_reports=len(feedback_reports),
        average_score=round(sum(scores) / len(scores), 2) if scores else None,
        best_score=max(scores) if scores else None,
        recent_score=get_recent_score(feedback_reports),
        common_missing_tones=get_common_missing_tones(feedback_reports),
    )


def ensure_user_exists(user_id: int, session: Session) -> User:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def get_latest_feedback_for_session(
    practice_session_id: int | None,
    session: Session,
) -> FeedbackReport | None:
    if practice_session_id is None:
        return None
    return session.exec(
        select(FeedbackReport)
        .where(FeedbackReport.practice_session_id == practice_session_id)
        .order_by(desc(FeedbackReport.created_at))
    ).first()


def get_recent_score(feedback_reports: list[FeedbackReport]) -> int | None:
    if not feedback_reports:
        return None

    latest_report = max(feedback_reports, key=lambda report: report.created_at)
    return latest_report.score


def get_common_missing_tones(feedback_reports: list[FeedbackReport]) -> list[dict]:
    counts: dict[str, int] = {}
    for report in feedback_reports:
        for chord in report.analysis.get("chords", []):
            expected = chord.get("expected", "unknown")
            for tone in chord.get("missing_tones", []):
                key = f"{expected}:{tone}"
                counts[key] = counts.get(key, 0) + 1

    return [
        {"chord": key.split(":", 1)[0], "tone": key.split(":", 1)[1], "count": count}
        for key, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
