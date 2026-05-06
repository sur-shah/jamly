# Jamly

Jamly is a **music practice assistant** for structured exercises and **quantitative audio feedback**. A learner (or a prototype app acting on their behalf) defines who they are and what they practice, receives a generated exercise, records a take, and receives a **feedback report** derived from signal processing on that recording—not from a live tutor in the room.

This repository is an **MVP**: a **FastAPI** service that owns users, exercises, sessions, file storage, analysis, and persisted reports, plus a small **Expo (React Native)** app in `mobile/` that exercises the same HTTP API.

## What Jamly does today

1. **Identity and preferences** — Create a user and store practice preferences (instrument, genre, skill level, focus, and similar fields). These influence how exercises are chosen or generated.
2. **Exercises** — Generate a **daily** exercise from preferences, or define a **custom** chord progression with metadata (key, tempo, title). The backend stores the exercise and expected harmony (e.g. required chord tones) for later comparison.
3. **Practice sessions** — Open a session that links a user to a single exercise attempt. A session tracks status from “planned” through upload and analysis to completion.
4. **Recordings** — Upload an audio (or container) file for that session. The file is stored on disk; the recording row is marked **uploaded**.
5. **Analysis** — Trigger analysis in a **separate step**. The backend decodes the clip, runs **librosa-based** feature extraction (duration, sample rate, tempo-related features, onsets, rhythm sufficiency flags), optionally enriches with **note events** when Basic Pitch is installed, compares windows to the exercise’s expected chords, computes a score, and saves a **feedback report** (coach-style summary, main fix, tip, and structured `analysis` JSON).
6. **Reading results** — List feedback for a session or fetch the latest report; the mobile app displays score, text, and chord-level detail when present.

In short: **Jamly turns an uploaded take plus an exercise definition into a saved, queryable coaching report.**

## Repository layout

This directory (the backend **project root**, next to `pyproject.toml`) contains:

```text
.
  app/                 # FastAPI routes, models, analyzer services
  tests/               # Pytest, including end-to-end API flow
  mobile/              # Expo app (npm) — calls the backend over HTTP
```

Run Python commands from **this** directory and app commands from **`mobile/`** unless noted otherwise.

## Requirements

- **Python** 3.11+ (see `pyproject.toml` for project metadata)
- **Node.js** and npm (for `mobile/`)
- Xcode / Android Studio or **Expo Go** on a device, if you run the mobile UI

## Run the backend

From the **project root** (the directory that contains `pyproject.toml`):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Defaults:

- **Database:** SQLite file `jamly.db` in the current working directory
- **Uploads:** directory `uploads/` for stored recording files

**Optional Postgres** — set `DATABASE_URL`, for example:

```bash
export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/jamly
```

**Docs** — interactive OpenAPI UI:

```text
http://127.0.0.1:8000/docs
```

For **physical phones or some emulators**, the backend must listen on every interface so the device can reach your machine:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Run the mobile app

See **`mobile/README.md`** for emulator-specific URLs. Typical flow:

```bash
cd mobile
npm install
npm run start
```

Point the app at your API:

- **Simulator on the same computer** — Often `http://127.0.0.1:8000` (configured via `EXPO_PUBLIC_API_URL` or the default in the app source).
- **Android emulator** — Use `http://10.0.2.2:8000`.
- **Physical device** — Use your laptop’s LAN IP, e.g. `http://192.168.1.20:8000`, with the server on `0.0.0.0`.

Example:

```bash
EXPO_PUBLIC_API_URL=http://YOUR_IP:8000 npm run start
```

The mobile MVP flow matches the API: create a **custom exercise**, create a **practice session**, **upload** a take, tap **analyze**, then read the feedback card.

## How the recording and analysis API works

Upload triggers analysis immediately — there is no separate analyze step:

| Step | Method | Purpose |
|------|--------|---------|
| Upload + analyze | `POST /practice-sessions/{practice_session_id}/recordings` | Accepts multipart `file`; runs analysis inline; returns `recording` (status `analyzed`) and a populated `feedback_report`. |
| List reports | `GET /practice-sessions/{practice_session_id}/feedback` | All feedback rows for the session. |
| Latest report | `GET /practice-sessions/{practice_session_id}/feedback/latest` | Most recent report. |

Other useful endpoints:

- **`POST /practice-sessions`** — Body: `user_id`, `exercise_id`.
- **`GET /practice-sessions/{practice_session_id}`** — Session status and metadata.

> **Note — no authentication yet.** All endpoints are open. User ownership is enforced only for exercise creation (an exercise must belong to the requesting user). Adding token-based auth is a planned next step.


### Swagger sequence (daily exercise path)

Use this order in `/docs`:

1. `POST /users`
2. `PUT /users/{user_id}/preferences`
3. `POST /exercises/daily?user_id={user_id}`
4. `POST /practice-sessions` with `user_id` and `exercise_id`
5. `POST /practice-sessions/{practice_session_id}/recordings` — upload audio; analysis runs immediately and the response includes the feedback report
6. `GET /practice-sessions/{practice_session_id}/feedback/latest` — confirm persisted report

Example:
<img width="760" height="1026" alt="image" src="https://github.com/user-attachments/assets/7d0b91c8-d033-45e4-92b8-ff45abec9232" />

<img width="416" height="486" alt="image" src="https://github.com/user-attachments/assets/f9e834a9-c61c-4faf-a6bd-f58fe3ed446b" />


For a **custom** progression, call `POST /exercises/custom` instead of `/exercises/daily`, then continue from step 4.

## Tests and lint

```bash
pytest
ruff check .
```

## Optional: richer note detection (Basic Pitch)

The analyzer can attach note-level data when **[Basic Pitch](https://github.com/spotify/basic-pitch)** is available. Without it, analysis still succeeds; note fields indicate unavailability.

On some macOS/Python stacks, pulling `basic-pitch` without care can conflict with TensorFlow variants. One workable approach documented in-repo:

```bash
pip install -e ".[dev,pitch]"
pip install basic-pitch --no-deps
```

If Basic Pitch fails to load, uploads and analysis remain usable; expect `analysis.notes.status` such as `unavailable` rather than full note events.

## Where logic lives

- **`app/services/exercise_generator.py`** — Rule-based daily exercise generation.
- **`app/services/analyzer.py`** — Audio features, scoring, chord-window comparison, feedback text construction.
- **`app/services/note_detector.py`** — Optional Basic Pitch integration.
- **`app/services/music_theory.py`** — Chord parsing and tone expectations.

This README describes the MVP as implemented in code; behaviour may evolve as Jamly grows.

---

## Development

Built with help from [Claude Code](https://claude.ai/code) and [OpenAI Codex](https://openai.com/index/openai-codex/) as AI coding assistants throughout development.
