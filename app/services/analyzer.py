from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import librosa
import numpy as np

from sqlmodel import Session

from app.models import (
    Exercise,
    FeedbackReport,
    PracticeSession,
    Recording,
    RecordingStatus,
    SessionStatus,
)
from app.services.note_detector import detect_notes


def analyze_recording(session: Session, recording: Recording) -> FeedbackReport:
    practice_session = session.get(PracticeSession, recording.practice_session_id)
    if practice_session is None:
        raise ValueError("Practice session not found")

    exercise = session.get(Exercise, practice_session.exercise_id)
    if exercise is None:
        raise ValueError("Exercise not found")

    recording.status = RecordingStatus.analyzing
    practice_session.status = SessionStatus.analyzing
    session.add(recording)
    session.add(practice_session)
    session.commit()
    session.refresh(recording)

    analysis = build_audio_feature_analysis(exercise, recording)
    report = FeedbackReport(
        practice_session_id=practice_session.id,
        recording_id=recording.id,
        score=analysis["score"],
        summary=analysis["coach_feedback"]["summary"],
        main_fix=analysis["coach_feedback"]["main_fix"],
        practice_tip=analysis["coach_feedback"]["practice_tip"],
        analysis=analysis,
    )

    recording.status = RecordingStatus.analyzed
    practice_session.status = SessionStatus.analyzed
    practice_session.completed_at = datetime.now(UTC)
    session.add(recording)
    session.add(practice_session)
    session.add(report)
    session.commit()
    session.refresh(report)
    return report


def build_audio_feature_analysis(exercise: Exercise, recording: Recording) -> dict[str, Any]:
    try:
        audio_features = extract_audio_features(Path(recording.file_path))
    except Exception as exc:
        return build_unreadable_audio_analysis(exercise, str(exc))

    expected_chords = exercise.target_analysis.get("expected_chords", exercise.chord_progression)
    first_focus = expected_chords[1] if len(expected_chords) > 1 else expected_chords[0]
    tempo_status = classify_tempo(audio_features, exercise.tempo_bpm)
    note_analysis = detect_notes(Path(recording.file_path))
    score = score_audio_features(tempo_status, audio_features["onset_count"])

    return {
        "mode": "audio_features",
        "score": score,
        "duration_seconds": audio_features["duration_seconds"],
        "sample_rate": audio_features["sample_rate"],
        "audio": {
            "duration_seconds": audio_features["duration_seconds"],
            "sample_rate": audio_features["sample_rate"],
            "channels": "mono",
        },
        "tempo": {
            "target_bpm": exercise.tempo_bpm,
            "estimated_bpm": audio_features["estimated_tempo_bpm"],
            "status": tempo_status,
        },
        "rhythm": {
            "onset_count": audio_features["onset_count"],
            "beat_count": audio_features["beat_count"],
            "onset_rate_per_second": audio_features["onset_rate_per_second"],
        },
        "notes": note_analysis,
        "chords": [
            {
                "expected": chord,
                "detected": None,
                "status": "not_analyzed_yet",
            }
            for chord in expected_chords
        ],
        "issues": build_audio_feature_issues(
            first_focus,
            tempo_status,
            audio_features,
            note_analysis,
        ),
        "coach_feedback": build_audio_feature_feedback(
            exercise,
            tempo_status,
            audio_features,
            note_analysis,
        ),
    }


def extract_audio_features(file_path: Path) -> dict[str, float | int]:
    y, sample_rate = librosa.load(file_path, sr=None, mono=True)
    if y.size == 0:
        raise ValueError("Uploaded audio file has no readable samples")

    duration_seconds = float(librosa.get_duration(y=y, sr=sample_rate))
    onset_envelope = librosa.onset.onset_strength(y=y, sr=sample_rate)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_envelope, sr=sample_rate)
    tempo_values, beat_frames = librosa.beat.beat_track(
        onset_envelope=onset_envelope,
        sr=sample_rate,
        units="frames",
    )

    estimated_tempo = float(np.atleast_1d(tempo_values)[0]) if np.size(tempo_values) else 0.0
    onset_count = int(len(onset_frames))
    beat_count = int(len(beat_frames))

    return {
        "duration_seconds": round(duration_seconds, 3),
        "sample_rate": int(sample_rate),
        "estimated_tempo_bpm": round(estimated_tempo, 2),
        "onset_count": onset_count,
        "beat_count": beat_count,
        "onset_rate_per_second": round(onset_count / duration_seconds, 3)
        if duration_seconds > 0
        else 0.0,
    }


def classify_tempo(audio_features: dict[str, float | int], target_bpm: int) -> str:
    estimated_bpm = float(audio_features["estimated_tempo_bpm"])
    duration_seconds = float(audio_features["duration_seconds"])
    beat_count = int(audio_features["beat_count"])
    onset_count = int(audio_features["onset_count"])

    if duration_seconds < 4 or beat_count < 4 or onset_count < 4:
        return "insufficient_rhythm"

    if estimated_bpm <= 0:
        return "unknown"

    difference = estimated_bpm - target_bpm
    if abs(difference) <= 3:
        return "on_target"
    if difference < -12:
        return "too_slow"
    if difference < -3:
        return "slightly_slow"
    if difference > 12:
        return "too_fast"
    return "slightly_fast"


def score_audio_features(tempo_status: str, onset_count: int) -> int:
    score = 80
    tempo_penalties = {
        "on_target": 0,
        "slightly_slow": 8,
        "slightly_fast": 8,
        "too_slow": 18,
        "too_fast": 18,
        "insufficient_rhythm": 4,
        "unknown": 15,
    }
    score -= tempo_penalties.get(tempo_status, 10)

    if onset_count == 0:
        score -= 20
    elif onset_count < 4:
        score -= 8

    return max(0, min(100, score))


def build_audio_feature_issues(
    first_focus: str,
    tempo_status: str,
    audio_features: dict[str, float | int],
    note_analysis: dict[str, Any],
) -> list[dict[str, str]]:
    issues = [
        {
            "type": "chord_quality",
            "chord": first_focus,
            "detail": (
                "Chord-note detection is not enabled yet. This baseline only checks audio "
                "duration, tempo, beats, and note/chord attack activity."
            ),
        }
    ]

    if tempo_status != "on_target":
        if tempo_status == "insufficient_rhythm":
            detail = (
                "This clip is too short or sparse to judge tempo reliably. Record a longer "
                "take with repeated strums or notes for timing feedback."
            )
        else:
            detail = (
                f"The estimated tempo is {audio_features['estimated_tempo_bpm']} BPM, "
                f"which is classified as {tempo_status.replace('_', ' ')}."
            )
        issues.append({"type": "timing", "detail": detail})

    if audio_features["onset_count"] == 0:
        issues.append(
            {
                "type": "audio_activity",
                "detail": "No clear note or chord attacks were detected in the recording.",
            }
        )

    if note_analysis["status"] != "analyzed":
        issues.append(
            {
                "type": "note_detection",
                "detail": (
                    "Basic Pitch note detection did not run successfully. "
                    f"Status: {note_analysis['status']}."
                ),
            }
        )

    return issues


def build_audio_feature_feedback(
    exercise: Exercise,
    tempo_status: str,
    audio_features: dict[str, float | int],
    note_analysis: dict[str, Any],
) -> dict[str, str]:
    if tempo_status == "on_target":
        main_fix = "Your tempo is close to the target. Next we need note-level analysis."
    elif tempo_status == "insufficient_rhythm":
        main_fix = "This clip is too short or sparse to judge tempo reliably."
    elif tempo_status == "unknown":
        main_fix = "The analyzer could not estimate a stable tempo from this recording."
    else:
        main_fix = (
            f"Your estimated tempo is {audio_features['estimated_tempo_bpm']} BPM "
            f"against the {exercise.tempo_bpm} BPM target."
        )

    if note_analysis["status"] == "analyzed":
        note_sentence = (
            f" Basic Pitch detected {note_analysis['count']} note event"
            f"{'' if note_analysis['count'] == 1 else 's'}."
        )
    else:
        note_sentence = " Note detection is not available for this take yet."

    return {
        "summary": (
            f"Analyzed {audio_features['duration_seconds']} seconds of audio for "
            f"{exercise.title}.{note_sentence}"
        ),
        "main_fix": main_fix,
        "practice_tip": (
            build_practice_tip(exercise, tempo_status)
        ),
    }


def build_practice_tip(exercise: Exercise, tempo_status: str) -> str:
    if tempo_status == "insufficient_rhythm":
        return (
            "Record the full progression with at least four steady strums or note attacks "
            "so Jamly has enough rhythm information to evaluate timing."
        )

    return (
        f"Practice with a metronome at {max(exercise.tempo_bpm - 10, 50)} BPM, then "
        f"record again at {exercise.tempo_bpm} BPM and compare the tempo estimate."
    )


def build_unreadable_audio_analysis(exercise: Exercise, error: str) -> dict[str, Any]:
    expected_chords = exercise.target_analysis.get("expected_chords", exercise.chord_progression)
    first_focus = expected_chords[1] if len(expected_chords) > 1 else expected_chords[0]

    return {
        "mode": "audio_unreadable",
        "score": 20,
        "error": error,
        "tempo": {
            "target_bpm": exercise.tempo_bpm,
            "estimated_bpm": None,
            "status": "unknown",
        },
        "rhythm": {
            "onset_count": 0,
            "beat_count": 0,
            "onset_rate_per_second": 0,
        },
        "notes": {
            "status": "not_run",
            "model": "basic_pitch",
            "note_events": [],
            "pitch_classes": [],
            "count": 0,
        },
        "chords": [
            {
                "expected": chord,
                "detected": None,
                "status": "not_analyzed_yet",
            }
            for chord in expected_chords
        ],
        "issues": [
            {
                "type": "audio_decode",
                "detail": "The uploaded file could not be decoded as audio.",
            },
            {
                "type": "chord_quality",
                "chord": first_focus,
                "detail": (
                    "Chord-note detection has not been enabled yet. Upload a valid WAV, MP3, "
                    "M4A, or other librosa-readable audio file for baseline timing analysis."
                ),
            },
        ],
        "coach_feedback": {
            "summary": "The practice loop worked, but the uploaded file was not readable audio.",
            "main_fix": "Upload a valid audio recording so Jamly can estimate tempo and rhythm.",
            "practice_tip": (
                "Try a short WAV or M4A recording from your phone or computer mic."
            ),
        },
    }
