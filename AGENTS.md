# AGENTS.md

This file gives coding agents the local project context they need to work on Jamly without rediscovering the basics each time.

## Project Overview

Jamly is an AI-powered music practice assistant. The current codebase is the backend API for a future mobile app.

Current backend capabilities:

- create users
- store user practice preferences
- generate daily genre/instrument exercises
- create practice sessions
- upload audio recordings
- run baseline audio analysis with `librosa`
- return saved feedback reports

The mobile app is not implemented yet.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLModel / SQLAlchemy
- SQLite by default for local development
- Postgres-ready via `DATABASE_URL`
- `librosa` and `soundfile` for baseline audio analysis
- Pytest for tests
- Ruff for linting

## Important Commands

From the repo root:

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

Run tests:

```bash
pytest
```

Run lint:

```bash
ruff check .
```

Install dependencies:

```bash
pip install -e ".[dev]"
```

## Project Layout

```text
app/
  main.py                       FastAPI app setup and route registration
  config.py                     Environment-driven settings
  database.py                   SQLModel engine/session helpers
  models.py                     Database models
  schemas.py                    API request/response schemas
  routes/
    users.py                    User and preference endpoints
    exercises.py                Daily exercise endpoints
    practice_sessions.py        Session, recording upload, feedback endpoints
  services/
    exercise_generator.py       Rule-based daily exercise generation
    analyzer.py                 Baseline audio analysis and feedback creation
tests/
  test_api_flow.py              End-to-end backend flow test
```

## Current API Flow

Use this sequence when manually testing in Swagger:

1. `POST /users`
2. `PUT /users/{user_id}/preferences`
3. `POST /exercises/daily?user_id={user_id}`
4. `POST /practice-sessions`
5. `POST /practice-sessions/{practice_session_id}/recordings`
6. `GET /practice-sessions/{practice_session_id}/feedback`

## Audio Analysis Status

The analyzer currently performs a real baseline pass:

- decodes uploaded audio
- extracts duration
- extracts sample rate
- estimates tempo
- counts beats and onsets

It does not yet detect chord tones or individual notes.

Current analysis modes:

- `audio_features`: audio decoded and baseline features extracted
- `audio_unreadable`: upload completed, but the file could not be decoded

Next intended audio step:

- add Basic Pitch note extraction
- convert detected MIDI notes to pitch classes
- compare detected tones with expected chord tones from the exercise

## Coding Guidelines

- Keep API response shapes stable when possible.
- Prefer small vertical slices over large rewrites.
- The analyzer should return structured facts first; coaching text should be derived from those facts.
- Do not make the LLM or feedback layer invent musical analysis that is not in the structured analysis.
- Keep user-facing music feedback cautious and confidence-based.
- Do not claim exact chord correctness until note/chord detection exists.
- Keep local development simple: SQLite and local file uploads are fine for now.
- Add tests for any meaningful API flow or analyzer behavior change.

## Generated/Local Files

Do not commit:

- `.venv/`
- `.env`
- `jamly.db`
- `uploads/`
- `*.egg-info/`
- `.pytest_cache/`
- `.ruff_cache/`

These are already covered by `.gitignore`.

## Future Architecture Direction

Near-term:

- keep one FastAPI service
- keep inline analysis until jobs become slow
- add Basic Pitch in `app/services/analyzer.py` or a nearby module

Later:

- move analysis to a background worker
- add Redis/Celery or another queue
- store recordings in object storage
- use Postgres in production
- connect a React Native or Expo mobile app
