from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import Genre, Instrument, PracticeFocus, RecordingStatus, SessionStatus, SkillLevel


class UserCreate(BaseModel):
    display_name: str = Field(
        examples=["Sur"],
        description="The name shown in the app.",
    )
    email: EmailStr | None = Field(
        default=None,
        examples=["sur@example.com"],
        description="Optional email for the user account.",
    )


class UserRead(BaseModel):
    id: int
    display_name: str
    email: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PreferenceUpsert(BaseModel):
    instrument: Instrument = Field(description="The instrument the user wants to practice.")
    genre: Genre = Field(description="The style of music the user wants to work on.")
    level: SkillLevel = Field(description="The user's current skill level.")
    focus: PracticeFocus = Field(
        default=PracticeFocus.chords,
        description="The main skill area for generated exercises.",
    )
    daily_minutes: int = Field(
        default=20,
        ge=5,
        le=180,
        description="How many minutes the user wants to practice each day.",
    )
    reminder_time: str | None = Field(
        default=None,
        examples=["18:00"],
        description="Optional daily reminder time in 24-hour HH:MM format.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "instrument": "guitar",
                "genre": "blues",
                "level": "beginner",
                "focus": "chords",
                "daily_minutes": 20,
                "reminder_time": "18:00",
            }
        }
    )


class PreferenceRead(PreferenceUpsert):
    id: int
    user_id: int
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExerciseRead(BaseModel):
    id: int
    user_id: int
    title: str
    instrument: Instrument
    genre: Genre
    level: SkillLevel
    focus: PracticeFocus
    key: str
    tempo_bpm: int
    chord_progression: list[str]
    steps: list[dict[str, Any]]
    target_analysis: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomExerciseCreate(BaseModel):
    user_id: int = Field(description="The id returned by POST /users.")
    title: str = Field(examples=["Four Chord Guitar Progression"])
    instrument: Instrument = Instrument.guitar
    genre: Genre = Genre.pop
    level: SkillLevel = SkillLevel.beginner
    focus: PracticeFocus = PracticeFocus.chords
    key: str = Field(default="G", examples=["G"])
    tempo_bpm: int = Field(default=80, ge=30, le=240)
    chord_progression: list[str] = Field(
        min_length=1,
        examples=[["Em", "C", "G", "D"]],
    )
    steps: list[dict[str, Any]] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": 1,
                "title": "Four Chord Guitar Progression",
                "instrument": "guitar",
                "genre": "pop",
                "level": "beginner",
                "focus": "chords",
                "key": "G",
                "tempo_bpm": 80,
                "chord_progression": ["Em", "C", "G", "D"],
            }
        }
    )


class PracticeSessionCreate(BaseModel):
    user_id: int = Field(description="The id returned by POST /users.")
    exercise_id: int = Field(description="The id returned by POST /exercises/daily.")

    model_config = ConfigDict(json_schema_extra={"example": {"user_id": 1, "exercise_id": 1}})


class PracticeSessionRead(BaseModel):
    id: int
    user_id: int
    exercise_id: int
    status: SessionStatus
    started_at: datetime
    completed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class RecordingRead(BaseModel):
    id: int
    practice_session_id: int
    original_filename: str
    content_type: str
    status: RecordingStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FeedbackReportRead(BaseModel):
    id: int
    practice_session_id: int
    recording_id: int
    score: int
    summary: str
    main_fix: str
    practice_tip: str
    analysis: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecordingUploadRead(BaseModel):
    recording: RecordingRead
    feedback_report: FeedbackReportRead | None = None
    message: str = "Recording uploaded."


class PracticeSessionSummaryRead(BaseModel):
    id: int
    exercise_id: int
    exercise_title: str
    status: SessionStatus
    started_at: datetime
    completed_at: datetime | None
    latest_score: int | None = None
    latest_summary: str | None = None


class PracticeStatsRead(BaseModel):
    user_id: int
    total_sessions: int
    completed_sessions: int
    total_recordings: int
    total_feedback_reports: int
    average_score: float | None
    best_score: int | None
    recent_score: int | None
    common_missing_tones: list[dict[str, Any]]
