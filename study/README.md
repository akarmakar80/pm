# Study Hub

A study website for a CBSE Class 10 student. The student types a topic, the site maps it to the
syllabus and shows a Topic Pack (Learn / Explore / Read / Practice) built only from verified sources.
Every opened topic is saved in My Library. Design: `docs/CBSE_STUDY_PLATFORM_PLAN.md`.

## Run with Docker

```bash
cp .env.example .env      # set passwords and, optionally, YOUTUBE_API_KEY
scripts/start.sh          # or scripts/start.ps1 on Windows; open http://localhost:3000
scripts/stop.sh
```

Accounts: `student`, `parent`, `educator`. Passwords come from `.env` when the database is first
created (default: same as the username). Data is stored in `data/study.db`.

## Local development

```bash
cd backend && uv venv && uv pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload --port 8000
.venv/bin/pytest tests

cd frontend && npm ci && npm run dev   # proxies /api to localhost:8000
```

## How content is verified

- Tier 1 (NCERT, CBSE, official channels) and tier 2 (Khan Academy, PhET) are shown immediately.
- Videos from allow-listed YouTube channels are indexed nightly and wait in Review until an educator
  scores them on the rubric (every score 3 or higher to approve).
- Educators can also add resources directly; their name and recommendation appear on the card.
- A student "Report a problem" hides the item until it is reviewed again.
- Syllabus data is in `backend/seed/syllabus.json` (2025-26). Check it against the CBSE curriculum
  each year.
