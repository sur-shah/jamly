from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any


NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def detect_notes(file_path: Path, max_notes: int = 200) -> dict[str, Any]:
    try:
        from basic_pitch.inference import predict
    except Exception as exc:
        return {
            "status": "unavailable",
            "model": "basic_pitch",
            "reason": (
                "Basic Pitch is not available in this environment. Install the optional "
                "pitch runtime to enable note detection."
            ),
            "error": str(exc),
            "note_events": [],
            "pitch_classes": [],
            "count": 0,
        }

    try:
        with redirect_stdout(StringIO()):
            _, _, note_events = predict(str(file_path))
    except Exception as exc:
        return {
            "status": "failed",
            "model": "basic_pitch",
            "error": str(exc),
            "note_events": [],
            "pitch_classes": [],
            "count": 0,
        }

    serialized_events = [
        serialize_basic_pitch_note_event(note_event)
        for note_event in note_events[:max_notes]
    ]
    pitch_classes = sorted({event["pitch_class"] for event in serialized_events})

    return {
        "status": "analyzed",
        "model": "basic_pitch",
        "count": len(note_events),
        "returned_count": len(serialized_events),
        "truncated": len(note_events) > max_notes,
        "pitch_classes": pitch_classes,
        "note_events": serialized_events,
    }


def serialize_basic_pitch_note_event(note_event: tuple) -> dict[str, Any]:
    start_seconds, end_seconds, midi_note, confidence, pitch_bends = note_event
    midi_note_int = int(midi_note)

    return {
        "start_seconds": round(float(start_seconds), 3),
        "end_seconds": round(float(end_seconds), 3),
        "midi": midi_note_int,
        "pitch": midi_to_pitch_name(midi_note_int),
        "pitch_class": midi_to_pitch_class(midi_note_int),
        "confidence": round(float(confidence), 3),
        "pitch_bend_count": len(pitch_bends or []),
    }


def midi_to_pitch_class(midi_note: int) -> str:
    return NOTE_NAMES[midi_note % 12]


def midi_to_pitch_name(midi_note: int) -> str:
    octave = (midi_note // 12) - 1
    return f"{midi_to_pitch_class(midi_note)}{octave}"
