# Jamly Backend

FastAPI backend for the Jamly AI music practice assistant.

Current MVP slice:

- user profile and music preferences
- daily exercise generation
- practice session creation
- audio recording upload
- placeholder recording analysis
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
