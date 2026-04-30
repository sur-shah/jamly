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
    tempo_status = classify_tempo(audio_features, exercise.tempo_bpm)
    note_analysis = detect_notes(Path(recording.file_path))
    analysis_windows = build_analysis_windows(
        expected_chords=expected_chords,
        duration_seconds=float(audio_features["duration_seconds"]),
        onset_times=audio_features["onset_times"],
        note_events=note_analysis.get("note_events", []),
    )
    chord_analysis = compare_chord_tones(
        analysis_windows=analysis_windows,
        required_tones=exercise.target_analysis.get("required_tones", {}),
    )
    score = score_audio_features(
        tempo_status,
        audio_features["onset_count"],
        chord_analysis=chord_analysis,
    )

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
            "onset_times": audio_features["onset_times"],
        },
        "notes": note_analysis,
        "analysis_windows": analysis_windows,
        "chords": chord_analysis,
        "issues": build_audio_feature_issues(
            tempo_status,
            audio_features,
            note_analysis,
            chord_analysis,
        ),
        "coach_feedback": build_audio_feature_feedback(
            exercise,
            tempo_status,
            audio_features,
            note_analysis,
            chord_analysis,
        ),
    }


def extract_audio_features(file_path: Path) -> dict[str, Any]:
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
        "onset_times": [
            round(float(onset_time), 3)
            for onset_time in librosa.frames_to_time(onset_frames, sr=sample_rate)
        ],
        "onset_rate_per_second": round(onset_count / duration_seconds, 3)
        if duration_seconds > 0
        else 0.0,
    }


def build_analysis_windows(
    expected_chords: list[str],
    duration_seconds: float,
    onset_times: list[float | int],
    note_events: list[dict[str, Any]],
    min_window_seconds: float = 1.0,
) -> list[dict[str, Any]]:
    if not expected_chords:
        return []

    starts, trigger = build_window_starts(
        expected_count=len(expected_chords),
        duration_seconds=duration_seconds,
        onset_times=[float(onset_time) for onset_time in onset_times],
        min_window_seconds=min_window_seconds,
    )
    end_boundaries = starts[1:] + [duration_seconds]

    return [
        {
            "index": index + 1,
            "expected_chord": expected_chords[index],
            "start_seconds": round(start_seconds, 3),
            "end_seconds": round(max(end_boundaries[index], start_seconds), 3),
            "trigger": trigger,
            "detected_tones": collect_pitch_classes_for_window(
                note_events,
                start_seconds=start_seconds,
                end_seconds=end_boundaries[index],
            ),
        }
        for index, start_seconds in enumerate(starts)
    ]


def build_window_starts(
    expected_count: int,
    duration_seconds: float,
    onset_times: list[float],
    min_window_seconds: float = 1.0,
) -> tuple[list[float], str]:
    if expected_count <= 0:
        return [], "fallback"
    if expected_count == 1:
        return [0.0], "single"

    grid_starts = build_grid_aligned_onset_starts(
        expected_count=expected_count,
        duration_seconds=duration_seconds,
        onset_times=onset_times,
        min_window_seconds=min_window_seconds,
    )
    if grid_starts is not None:
        return grid_starts, "grid_onset"

    return build_first_spaced_onset_starts(
        expected_count=expected_count,
        duration_seconds=duration_seconds,
        onset_times=onset_times,
        min_window_seconds=min_window_seconds,
    )


def build_grid_aligned_onset_starts(
    expected_count: int,
    duration_seconds: float,
    onset_times: list[float],
    min_window_seconds: float = 1.0,
) -> list[float] | None:
    if duration_seconds <= 0:
        return None

    section_seconds = duration_seconds / expected_count
    search_radius = max(section_seconds * 0.45, min_window_seconds)
    usable_onsets = sorted(onset for onset in onset_times if onset >= 0.05)
    starts = [0.0]

    for boundary_index in range(1, expected_count):
        target = section_seconds * boundary_index
        candidates = [
            onset
            for onset in usable_onsets
            if abs(onset - target) <= search_radius
            and onset - starts[-1] >= min_window_seconds
        ]
        if not candidates:
            return None

        starts.append(min(candidates, key=lambda onset: abs(onset - target)))

    return starts


def build_first_spaced_onset_starts(
    expected_count: int,
    duration_seconds: float,
    onset_times: list[float],
    min_window_seconds: float = 1.0,
) -> tuple[list[float], str]:
    starts = [0.0]

    for onset_time in sorted(onset_times):
        if onset_time < 0.05:
            continue
        if onset_time - starts[-1] < min_window_seconds:
            continue
        starts.append(onset_time)
        if len(starts) == expected_count:
            break

    if len(starts) < expected_count:
        return build_equal_window_starts(expected_count, duration_seconds), "fallback"

    return starts, "onset"


def build_equal_window_starts(expected_count: int, duration_seconds: float) -> list[float]:
    if expected_count <= 0:
        return []

    window_seconds = duration_seconds / expected_count if duration_seconds > 0 else 0
    return [round(window_seconds * index, 3) for index in range(expected_count)]


def collect_pitch_classes_for_window(
    note_events: list[dict[str, Any]],
    start_seconds: float,
    end_seconds: float,
) -> list[str]:
    pitch_classes = {
        note_event["pitch_class"]
        for note_event in note_events
        if note_event_overlaps_window(note_event, start_seconds, end_seconds)
    }
    return sorted(pitch_classes)


def note_event_overlaps_window(
    note_event: dict[str, Any],
    start_seconds: float,
    end_seconds: float,
) -> bool:
    note_start = float(note_event["start_seconds"])
    note_end = float(note_event["end_seconds"])
    return note_start < end_seconds and note_end > start_seconds


def compare_chord_tones(
    analysis_windows: list[dict[str, Any]],
    required_tones: dict[str, list[str]],
) -> list[dict[str, Any]]:
    return [
        compare_window_to_expected_chord(window, required_tones)
        for window in analysis_windows
    ]


def compare_window_to_expected_chord(
    window: dict[str, Any],
    required_tones: dict[str, list[str]],
) -> dict[str, Any]:
    expected_chord = window["expected_chord"]
    required = required_tones.get(expected_chord, [])
    detected = window.get("detected_tones", [])
    missing = [tone for tone in required if tone not in detected]
    extra = [tone for tone in detected if tone not in required]
    matched_count = len(required) - len(missing)
    match_ratio = round(matched_count / len(required), 3) if required else 0.0

    return {
        "index": window["index"],
        "expected": expected_chord,
        "start_seconds": window["start_seconds"],
        "end_seconds": window["end_seconds"],
        "required_tones": required,
        "detected_tones": detected,
        "missing_tones": missing,
        "extra_tones": extra,
        "match_ratio": match_ratio,
        "status": classify_chord_match(required, detected, missing),
    }


def classify_chord_match(
    required_tones: list[str],
    detected_tones: list[str],
    missing_tones: list[str],
) -> str:
    if not required_tones:
        return "unknown_chord"
    if not detected_tones:
        return "not_detected"
    if not missing_tones:
        return "matched"
    if len(missing_tones) == len(required_tones):
        return "not_detected"
    return "incomplete"


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


def score_audio_features(
    tempo_status: str,
    onset_count: int,
    chord_analysis: list[dict[str, Any]] | None = None,
) -> int:
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

    if chord_analysis:
        average_match = sum(chord["match_ratio"] for chord in chord_analysis) / len(chord_analysis)
        score += round((average_match - 0.75) * 20)

    return max(0, min(100, score))


def build_audio_feature_issues(
    tempo_status: str,
    audio_features: dict[str, float | int],
    note_analysis: dict[str, Any],
    chord_analysis: list[dict[str, Any]],
) -> list[dict[str, str]]:
    issues = []

    chord_issue = build_chord_issue(chord_analysis)
    if chord_issue is not None:
        issues.append(chord_issue)

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


def build_chord_issue(chord_analysis: list[dict[str, Any]]) -> dict[str, str] | None:
    problem_chords = [
        chord for chord in chord_analysis
        if chord["status"] in {"incomplete", "not_detected", "unknown_chord"}
    ]
    if not problem_chords:
        return None

    chord = min(problem_chords, key=lambda item: item["match_ratio"])
    if chord["status"] == "unknown_chord":
        detail = f"Jamly does not know the required tones for {chord['expected']} yet."
    elif chord["missing_tones"]:
        missing = ", ".join(chord["missing_tones"])
        detail = f"{chord['expected']} is missing or underplaying: {missing}."
    else:
        detail = f"{chord['expected']} was not detected clearly in its window."

    return {
        "type": "chord_quality",
        "chord": chord["expected"],
        "detail": detail,
    }


def build_audio_feature_feedback(
    exercise: Exercise,
    tempo_status: str,
    audio_features: dict[str, float | int],
    note_analysis: dict[str, Any],
    chord_analysis: list[dict[str, Any]],
) -> dict[str, str]:
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
        "main_fix": build_main_fix(exercise, tempo_status, audio_features, chord_analysis),
        "practice_tip": (
            build_practice_tip(exercise, tempo_status, chord_analysis)
        ),
    }


def build_main_fix(
    exercise: Exercise,
    tempo_status: str,
    audio_features: dict[str, float | int],
    chord_analysis: list[dict[str, Any]],
) -> str:
    chord_issue = build_chord_issue(chord_analysis)
    if chord_issue is not None:
        return chord_issue["detail"]

    if tempo_status == "on_target":
        return "Your chord tones and tempo are close to the target."
    if tempo_status == "insufficient_rhythm":
        return "The chord tones look close, but this clip is too short or sparse to judge tempo."
    if tempo_status == "unknown":
        return "The chord tones look close, but the analyzer could not estimate a stable tempo."

    return (
        f"Your estimated tempo is {audio_features['estimated_tempo_bpm']} BPM "
        f"against the {exercise.tempo_bpm} BPM target."
    )


def build_practice_tip(
    exercise: Exercise,
    tempo_status: str,
    chord_analysis: list[dict[str, Any]],
) -> str:
    chord_issue = build_chord_issue(chord_analysis)
    if chord_issue is not None:
        return (
            "Slow the progression down and make sure each missing tone rings inside its "
            "chord window before moving on."
        )

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
        "analysis_windows": [],
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
                    "Upload a valid WAV, MP3, M4A, or other librosa-readable audio file "
                    "for baseline timing and chord-tone analysis."
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
