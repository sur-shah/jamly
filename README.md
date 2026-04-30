# Jamly Backend

FastAPI backend for the Jamly AI music practice assistant.

Current MVP slice:

- user profile and music preferences
- daily exercise generation
- custom exercise creation
- practice session creation
- audio recording upload
- audio feature, note, window, and chord-tone analysis
- feedback report retrieval

## Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

By default the app uses local SQLite at `jamly.db` and local uploaded files in `uploads/`.
Set `DATABASE_URL` to Postgres later, for example:

```bash
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/jamly
```

## API Docs

Once running, open:

```text
http://127.0.0.1:8000/docs
```

Useful Swagger flow for testing a custom progression:

```text
POST /users
POST /exercises/custom
POST /practice-sessions
POST /practice-sessions/{practice_session_id}/recordings
GET /practice-sessions/{practice_session_id}/feedback/latest
```

## Optional Basic Pitch Notes

The analyzer can use Spotify Basic Pitch for note-event detection when it is installed.
On this Mac/Python 3.12 setup, the normal `basic-pitch` dependency install tries to pull an incompatible `tensorflow-macos` version, so use the CoreML runtime workaround:

```bash
pip install -e ".[dev,pitch]"
pip install basic-pitch --no-deps
```

If Basic Pitch is unavailable, uploads still work and `analysis.notes.status` will be `unavailable`.
