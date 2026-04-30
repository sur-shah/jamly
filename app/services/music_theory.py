NOTE_SEQUENCE = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")

FLAT_TO_SHARP = {
    "Db": "C#",
    "Eb": "D#",
    "Gb": "F#",
    "Ab": "G#",
    "Bb": "A#",
}

CHORD_INTERVALS = {
    "": (0, 4, 7),
    "m": (0, 3, 7),
    "min": (0, 3, 7),
    "5": (0, 7),
    "7": (0, 4, 7, 10),
    "m7": (0, 3, 7, 10),
    "min7": (0, 3, 7, 10),
    "maj7": (0, 4, 7, 11),
}


def build_required_tones(chords: list[str]) -> dict[str, list[str]]:
    return {chord: get_required_tones(chord) for chord in chords}


def get_required_tones(chord: str) -> list[str]:
    root, quality = parse_chord_symbol(chord)
    if quality not in CHORD_INTERVALS:
        raise ValueError(f"Unsupported chord quality '{quality}' in chord '{chord}'")

    root_index = NOTE_SEQUENCE.index(root)
    return [
        NOTE_SEQUENCE[(root_index + interval) % len(NOTE_SEQUENCE)]
        for interval in CHORD_INTERVALS[quality]
    ]


def parse_chord_symbol(chord: str) -> tuple[str, str]:
    normalized = chord.strip()
    if not normalized:
        raise ValueError("Chord symbol cannot be empty")

    if len(normalized) >= 2 and normalized[1] in {"#", "b"}:
        root = normalized[:2]
        quality = normalized[2:]
    else:
        root = normalized[0]
        quality = normalized[1:]

    root = FLAT_TO_SHARP.get(root, root)
    if root not in NOTE_SEQUENCE:
        raise ValueError(f"Unsupported chord root '{root}' in chord '{chord}'")

    return root, quality
