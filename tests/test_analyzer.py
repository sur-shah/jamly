from app.services.analyzer import (
    build_analysis_windows,
    build_feedback_summary,
    build_grid_aligned_onset_starts,
    build_main_fix,
    build_practice_tip,
    compare_chord_tones,
    compare_window_to_expected_chord,
    build_window_starts,
    classify_tempo,
    collect_pitch_classes_for_window,
)
from app.models import Exercise, Genre, Instrument, PracticeFocus, SkillLevel


def test_classify_tempo_requires_enough_rhythm_evidence() -> None:
    assert (
        classify_tempo(
            {
                "duration_seconds": 2.3,
                "estimated_tempo_bpm": 152,
                "beat_count": 7,
                "onset_count": 5,
            },
            target_bpm=80,
        )
        == "insufficient_rhythm"
    )

    assert (
        classify_tempo(
            {
                "duration_seconds": 8.0,
                "estimated_tempo_bpm": 152,
                "beat_count": 7,
                "onset_count": 2,
            },
            target_bpm=80,
        )
        == "insufficient_rhythm"
    )


def test_classify_tempo_uses_estimated_bpm_when_rhythm_is_sufficient() -> None:
    assert (
        classify_tempo(
            {
                "duration_seconds": 8.0,
                "estimated_tempo_bpm": 152,
                "beat_count": 7,
                "onset_count": 6,
            },
            target_bpm=80,
        )
        == "too_fast"
    )

    assert (
        classify_tempo(
            {
                "duration_seconds": 8.0,
                "estimated_tempo_bpm": 81.5,
                "beat_count": 7,
                "onset_count": 6,
            },
            target_bpm=80,
        )
        == "on_target"
    )


def test_build_window_starts_uses_spaced_onsets_when_enough_exist() -> None:
    starts, trigger = build_window_starts(
        expected_count=2,
        duration_seconds=5,
        onset_times=[0.2, 0.5, 2.6, 2.9],
        min_window_seconds=1,
    )

    assert trigger == "grid_onset"
    assert starts == [0.0, 2.6]


def test_build_window_starts_falls_back_when_onsets_are_not_useful() -> None:
    starts, trigger = build_window_starts(
        expected_count=4,
        duration_seconds=8,
        onset_times=[0.1, 0.3],
        min_window_seconds=1,
    )

    assert trigger == "fallback"
    assert starts == [0.0, 2.0, 4.0, 6.0]


def test_collect_pitch_classes_for_window_uses_note_overlap() -> None:
    note_events = [
        {"pitch_class": "A", "start_seconds": 0.2, "end_seconds": 1.0},
        {"pitch_class": "C#", "start_seconds": 0.8, "end_seconds": 1.4},
        {"pitch_class": "D", "start_seconds": 2.1, "end_seconds": 3.0},
    ]

    assert collect_pitch_classes_for_window(note_events, 0, 2) == ["A", "C#"]


def test_build_analysis_windows_assigns_notes_to_expected_chords() -> None:
    windows = build_analysis_windows(
        expected_chords=["A", "D"],
        duration_seconds=5,
        onset_times=[0.2, 2.6],
        note_events=[
            {"pitch_class": "A", "start_seconds": 0.2, "end_seconds": 1.0},
            {"pitch_class": "C#", "start_seconds": 0.8, "end_seconds": 1.4},
            {"pitch_class": "E", "start_seconds": 1.1, "end_seconds": 2.4},
            {"pitch_class": "D", "start_seconds": 2.8, "end_seconds": 3.6},
            {"pitch_class": "F#", "start_seconds": 3.1, "end_seconds": 4.0},
        ],
    )

    assert windows == [
        {
            "index": 1,
            "expected_chord": "A",
            "start_seconds": 0.0,
            "end_seconds": 2.6,
            "trigger": "grid_onset",
            "detected_tones": ["A", "C#", "E"],
        },
        {
            "index": 2,
            "expected_chord": "D",
            "start_seconds": 2.6,
            "end_seconds": 5,
            "trigger": "grid_onset",
            "detected_tones": ["D", "F#"],
        },
    ]


def test_grid_aligned_onset_starts_prefer_likely_section_boundaries() -> None:
    starts = build_grid_aligned_onset_starts(
        expected_count=4,
        duration_seconds=8.452,
        onset_times=[0.104, 0.139, 0.987, 1.8, 3.042, 3.866, 4.342, 5.968, 7.291, 8.057],
        min_window_seconds=1,
    )

    assert starts == [0.0, 1.8, 4.342, 5.968]


def test_grid_aligned_onset_starts_returns_none_when_boundaries_are_missing() -> None:
    starts = build_grid_aligned_onset_starts(
        expected_count=4,
        duration_seconds=8,
        onset_times=[0.1, 0.3],
        min_window_seconds=1,
    )

    assert starts is None


def test_compare_window_to_expected_chord_marks_match() -> None:
    comparison = compare_window_to_expected_chord(
        {
            "index": 1,
            "expected_chord": "Em",
            "start_seconds": 0,
            "end_seconds": 2,
            "detected_tones": ["B", "E", "G"],
        },
        {"Em": ["E", "G", "B"]},
    )

    assert comparison == {
        "index": 1,
        "expected": "Em",
        "start_seconds": 0,
        "end_seconds": 2,
        "required_tones": ["E", "G", "B"],
        "detected_tones": ["B", "E", "G"],
        "missing_tones": [],
        "extra_tones": [],
        "match_ratio": 1.0,
        "status": "matched",
    }


def test_compare_window_to_expected_chord_marks_missing_tones() -> None:
    comparison = compare_window_to_expected_chord(
        {
            "index": 1,
            "expected_chord": "A7",
            "start_seconds": 0,
            "end_seconds": 2,
            "detected_tones": ["A", "C#", "E"],
        },
        {"A7": ["A", "C#", "E", "G"]},
    )

    assert comparison["missing_tones"] == ["G"]
    assert comparison["match_ratio"] == 0.75
    assert comparison["status"] == "incomplete"


def test_compare_chord_tones_handles_unknown_chords() -> None:
    comparisons = compare_chord_tones(
        [
            {
                "index": 1,
                "expected_chord": "Mystery",
                "start_seconds": 0,
                "end_seconds": 2,
                "detected_tones": ["A"],
            }
        ],
        {},
    )

    assert comparisons[0]["required_tones"] == []
    assert comparisons[0]["status"] == "unknown_chord"


def test_feedback_summary_counts_matched_chords_and_extra_tones() -> None:
    summary = build_feedback_summary(
        exercise=build_test_exercise(),
        audio_features={"duration_seconds": 8.4},
        chord_analysis=[
            {"expected": "Em", "status": "matched", "extra_tones": []},
            {"expected": "C", "status": "matched", "extra_tones": ["B"]},
            {"expected": "G", "status": "matched", "extra_tones": ["E"]},
            {"expected": "D", "status": "matched", "extra_tones": []},
        ],
        note_sentence=" Basic Pitch detected 79 note events.",
    )

    assert summary == (
        "Matched 4 of 4 expected chords for Test Progression. Basic Pitch detected "
        "79 note events. Extra ringing tones appeared in C and G."
    )


def test_main_fix_prioritizes_missing_tones() -> None:
    main_fix = build_main_fix(
        exercise=build_test_exercise(),
        tempo_status="on_target",
        audio_features={"estimated_tempo_bpm": 80},
        chord_analysis=[
            {
                "expected": "A7",
                "status": "incomplete",
                "missing_tones": ["G"],
                "match_ratio": 0.75,
                "extra_tones": [],
            }
        ],
    )

    assert main_fix == "A7 is missing or underplaying: G."


def test_practice_tip_mentions_clean_releases_for_extra_tones() -> None:
    practice_tip = build_practice_tip(
        exercise=build_test_exercise(),
        tempo_status="on_target",
        chord_analysis=[
            {"expected": "C", "status": "matched", "extra_tones": ["B"]},
        ],
    )

    assert practice_tip == (
        "Practice muting and clean releases between chord changes so old strings do "
        "not keep ringing into the next chord."
    )


def build_test_exercise() -> Exercise:
    return Exercise(
        user_id=1,
        title="Test Progression",
        instrument=Instrument.guitar,
        genre=Genre.pop,
        level=SkillLevel.beginner,
        focus=PracticeFocus.chords,
        key="G",
        tempo_bpm=80,
        chord_progression=["Em", "C", "G", "D"],
        steps=[],
        target_analysis={},
    )
