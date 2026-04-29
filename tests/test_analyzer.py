from app.services.analyzer import classify_tempo


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
