from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, desc, select

from app.database import get_session
from app.models import Exercise, User, UserPreference
from app.schemas import ExerciseRead
from app.services.exercise_generator import build_daily_exercise

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.post("/daily", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
def create_daily_exercise(user_id: int, session: Session = Depends(get_session)) -> Exercise:
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    preference = session.exec(
        select(UserPreference).where(UserPreference.user_id == user_id)
    ).first()
    if preference is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Set user preferences before generating an exercise",
        )

    plan = build_daily_exercise(preference)
    exercise = Exercise(user_id=user_id, **plan)
    session.add(exercise)
    session.commit()
    session.refresh(exercise)
    return exercise


@router.get("/today", response_model=ExerciseRead)
def get_latest_exercise(user_id: int, session: Session = Depends(get_session)) -> Exercise:
    exercise = session.exec(
        select(Exercise).where(Exercise.user_id == user_id).order_by(desc(Exercise.created_at))
    ).first()
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise


@router.get("/{exercise_id}", response_model=ExerciseRead)
def get_exercise(exercise_id: int, session: Session = Depends(get_session)) -> Exercise:
    exercise = session.get(Exercise, exercise_id)
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return exercise
