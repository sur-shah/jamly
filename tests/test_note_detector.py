from app.services.note_detector import midi_to_pitch_class, midi_to_pitch_name


def test_midi_note_conversion() -> None:
    assert midi_to_pitch_class(69) == "A"
    assert midi_to_pitch_name(69) == "A4"
    assert midi_to_pitch_class(61) == "C#"
    assert midi_to_pitch_name(61) == "C#4"
