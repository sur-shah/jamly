import io
import math
import struct
import wave
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app


def test_recording_based_practice_flow(tmp_path: Path) -> None:
    settings = get_settings()
    settings.upload_dir = str(tmp_path / "uploads")

    with TestClient(app) as client:
        user_response = client.post(
            "/users",
            json={"display_name": "Sur", "email": "sur@example.com"},
        )
        assert user_response.status_code == 201
        user_id = user_response.json()["id"]

        preference_response = client.put(
            f"/users/{user_id}/preferences",
            json={
                "instrument": "guitar",
                "genre": "blues",
                "level": "beginner",
                "focus": "chords",
                "daily_minutes": 20,
            },
        )
        assert preference_response.status_code == 200

        exercise_response = client.post("/exercises/daily", params={"user_id": user_id})
        assert exercise_response.status_code == 201
        exercise = exercise_response.json()
        assert exercise["chord_progression"] == ["A7", "D7", "A7", "E7"]

        session_response = client.post(
            "/practice-sessions",
            json={"user_id": user_id, "exercise_id": exercise["id"]},
        )
        assert session_response.status_code == 201
        practice_session_id = session_response.json()["id"]

        recording_response = client.post(
            f"/practice-sessions/{practice_session_id}/recordings",
            files={"file": ("take.wav", build_test_wav(), "audio/wav")},
        )
        assert recording_response.status_code == 200
        upload_result = recording_response.json()
        assert upload_result["recording"]["status"] == "analyzed"
        assert upload_result["feedback_report"]["analysis"]["mode"] == "audio_features"
        assert upload_result["feedback_report"]["analysis"]["duration_seconds"] > 0

        feedback_response = client.get(f"/practice-sessions/{practice_session_id}/feedback")
        assert feedback_response.status_code == 200
        feedback = feedback_response.json()
        assert len(feedback) == 1
        assert feedback[0]["analysis"]["mode"] == "audio_features"


def build_test_wav() -> bytes:
    sample_rate = 16_000
    duration_seconds = 2
    frequency_hz = 440
    frames = bytearray()

    for index in range(sample_rate * duration_seconds):
        sample = 0.35 * math.sin(2 * math.pi * frequency_hz * index / sample_rate)
        frames.extend(struct.pack("<h", int(sample * 32767)))

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))

    return buffer.getvalue()
