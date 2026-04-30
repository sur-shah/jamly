import pytest

from app.services.music_theory import build_required_tones, get_required_tones


def test_get_required_tones_for_common_chords() -> None:
    assert get_required_tones("C") == ["C", "E", "G"]
    assert get_required_tones("Em") == ["E", "G", "B"]
    assert get_required_tones("A7") == ["A", "C#", "E", "G"]
    assert get_required_tones("Bb") == ["A#", "D", "F"]


def test_build_required_tones_for_progression() -> None:
    assert build_required_tones(["Em", "C", "G", "D"]) == {
        "Em": ["E", "G", "B"],
        "C": ["C", "E", "G"],
        "G": ["G", "B", "D"],
        "D": ["D", "F#", "A"],
    }


def test_get_required_tones_rejects_unknown_chord_quality() -> None:
    with pytest.raises(ValueError, match="Unsupported chord quality"):
        get_required_tones("Csus4")
