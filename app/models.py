from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def utc_now() -> datetime:
    return datetime.now(UTC)


class Instrument(str, Enum):
    guitar = "guitar"
    piano = "piano"
    bass = "bass"
    voice = "voice"


class Genre(str, Enum):
    blues = "blues"
    jazz = "jazz"
    pop = "pop"
    rock = "rock"
    rnb = "rnb"


class SkillLevel(str, Enum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class PracticeFocus(str, Enum):
    chords = "chords"
    rhythm = "rhythm"
    scales = "scales"
    improvisation = "improvisation"


class SessionStatus(str, Enum):
    planned = "planned"
    recording_uploaded = "recording_uploaded"
    analyzing = "analyzing"
    analyzed = "analyzed"
    failed = "failed"


class RecordingStatus(str, Enum):
    uploaded = "uploaded"
    analyzing = "analyzing"
    analyzed = "analyzed"
    failed = "failed"


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    display_name: str
    email: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class UserPreference(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    instrument: Instrument
    genre: Genre
    level: SkillLevel
    focus: PracticeFocus = PracticeFocus.chords
    daily_minutes: int = 20
    reminder_time: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class Exercise(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    instrument: Instrument
    genre: Genre
    level: SkillLevel
    focus: PracticeFocus
    key: str
    tempo_bpm: int
    chord_progression: list[str] = Field(sa_column=Column(JSON))
    steps: list[dict[str, Any]] = Field(sa_column=Column(JSON))
    target_analysis: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now, index=True)


class PracticeSession(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    status: SessionStatus = SessionStatus.planned
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None


class Recording(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    practice_session_id: int = Field(foreign_key="practicesession.id", index=True)
    original_filename: str
    file_path: str
    content_type: str
    status: RecordingStatus = RecordingStatus.uploaded
    created_at: datetime = Field(default_factory=utc_now)


class FeedbackReport(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    practice_session_id: int = Field(foreign_key="practicesession.id", index=True)
    recording_id: int = Field(foreign_key="recording.id", index=True)
    score: int
    summary: str
    main_fix: str
    practice_tip: str
    analysis: dict[str, Any] = Field(sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now)
