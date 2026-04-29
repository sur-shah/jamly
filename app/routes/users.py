from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, UserPreference
from app.schemas import PreferenceRead, PreferenceUpsert, UserCreate, UserRead

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
