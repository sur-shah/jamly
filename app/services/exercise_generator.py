from app.models import Genre, Instrument, PracticeFocus, SkillLevel, UserPreference


def build_daily_exercise(preference: UserPreference) -> dict:
    genre_plans = {
        Genre.blues: {
            "title": "12-Bar Blues Chord Loop",
            "key": "A",
            "tempo_bpm": 80,
            "chord_progression": ["A7", "D7", "A7", "E7"],
            "steps": [
                {"minutes": 3, "label": "Warm up dominant 7 shapes in A and D."},
                {"minutes": 7, "label": "Loop A7 to D7 with a steady downstroke pulse."},
                {"minutes": 7, "label": "Play the full I-IV-V progression with a metronome."},
                {"minutes": 3, "label": "Record one clean take without stopping."},
            ],
            "target_analysis": {
                "expected_chords": ["A7", "D7", "A7", "E7"],
                "required_tones": {
                    "A7": ["A", "C#", "E", "G"],
                    "D7": ["D", "F#", "A", "C"],
                    "E7": ["E", "G#", "B", "D"],
                },
            },
        },
        Genre.jazz: {
            "title": "Beginner ii-V-I Shell Voicings",
            "key": "C",
            "tempo_bpm": 70,
            "chord_progression": ["Dm7", "G7", "Cmaj7"],
            "steps": [
                {"minutes": 4, "label": "Play guide tones for Dm7, G7, and Cmaj7."},
                {"minutes": 8, "label": "Loop the ii-V-I progression with relaxed timing."},
                {"minutes": 5, "label": "Record four steady passes at the target tempo."},
            ],
            "target_analysis": {
                "expected_chords": ["Dm7", "G7", "Cmaj7"],
                "required_tones": {
                    "Dm7": ["D", "F", "A", "C"],
                    "G7": ["G", "B", "D", "F"],
                    "Cmaj7": ["C", "E", "G", "B"],
                },
            },
        },
        Genre.pop: {
            "title": "I-V-vi-IV Chord Flow",
            "key": "C",
            "tempo_bpm": 86,
            "chord_progression": ["C", "G", "Am", "F"],
            "steps": [
                {"minutes": 3, "label": "Practice each chord shape cleanly."},
                {"minutes": 8, "label": "Loop the progression without pausing between chords."},
                {"minutes": 5, "label": "Record a take with steady quarter-note pulse."},
            ],
            "target_analysis": {
                "expected_chords": ["C", "G", "Am", "F"],
                "required_tones": {
                    "C": ["C", "E", "G"],
                    "G": ["G", "B", "D"],
                    "Am": ["A", "C", "E"],
                    "F": ["F", "A", "C"],
                },
            },
        },
        Genre.rock: {
            "title": "Power Chord Transition Drill",
            "key": "E",
            "tempo_bpm": 92,
            "chord_progression": ["E5", "G5", "A5", "B5"],
            "steps": [
                {"minutes": 4, "label": "Warm up with muted eighth notes."},
                {"minutes": 8, "label": "Move through the power chords with even attacks."},
                {"minutes": 4, "label": "Record one tight take at the target tempo."},
            ],
            "target_analysis": {
                "expected_chords": ["E5", "G5", "A5", "B5"],
                "required_tones": {
                    "E5": ["E", "B"],
                    "G5": ["G", "D"],
                    "A5": ["A", "E"],
                    "B5": ["B", "F#"],
                },
            },
        },
        Genre.rnb: {
            "title": "Smooth Minor Seventh Groove",
            "key": "A",
            "tempo_bpm": 76,
            "chord_progression": ["Am7", "Dm7", "Em7", "Dm7"],
            "steps": [
                {"minutes": 4, "label": "Voice each minor seventh chord slowly."},
                {"minutes": 8, "label": "Loop the progression with a soft, even groove."},
                {"minutes": 5, "label": "Record the smoothest take you can."},
            ],
            "target_analysis": {
                "expected_chords": ["Am7", "Dm7", "Em7", "Dm7"],
                "required_tones": {
                    "Am7": ["A", "C", "E", "G"],
                    "Dm7": ["D", "F", "A", "C"],
                    "Em7": ["E", "G", "B", "D"],
                },
            },
        },
    }

    plan = genre_plans[preference.genre].copy()
    plan["instrument"] = preference.instrument
    plan["genre"] = preference.genre
    plan["level"] = preference.level
    plan["focus"] = preference.focus

    if preference.level == SkillLevel.advanced:
        plan["tempo_bpm"] += 18
    elif preference.level == SkillLevel.intermediate:
        plan["tempo_bpm"] += 8

    if preference.instrument == Instrument.voice:
        plan["focus"] = PracticeFocus.scales
        plan["steps"] = [
            {"minutes": 4, "label": "Sing the chord tones slowly against a drone."},
            {"minutes": 8, "label": "Sing each arpeggio in time with a metronome."},
            {"minutes": 4, "label": "Record one pass and listen for pitch center."},
        ]

    return plan
