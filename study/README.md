# Study Hub

A study website for a CBSE Class 10 student. Type a topic, and the site shows videos, simulations,
the NCERT chapter and practice for it. Every opened topic is saved in My Library.
Design: `docs/CBSE_STUDY_PLATFORM_PLAN.md`.

## Run with Docker

```bash
cp .env.example .env      # add YOUTUBE_API_KEY and OPENROUTER_API_KEY
scripts/start.sh          # or scripts/start.ps1 on Windows; open http://localhost:3000
scripts/stop.sh
```

There is no login. Data is stored in `data/study.db`.

## Local development

```bash
cd backend && uv venv && uv pip install -r requirements.txt
.venv/bin/uvicorn app:app --reload --port 8000
.venv/bin/pytest tests

cd frontend && npm ci && npm run dev   # proxies /api to localhost:8000
```

## How it works

- **Videos**: the first time a topic is opened, YouTube is searched once (Education category,
  SafeSearch strict). Age-restricted, non-embeddable, very short, other-class and blocked-word videos
  are dropped; the rest are ranked by views, engagement, length, recency and known CBSE channels.
  Results are saved, so later visits are instant. "Find more videos" searches again.
- **Other material**: NCERT chapter PDFs, PhET simulations and Khan Academy are built in.
  Sites that need an account show a "Sign in" link (see Learning sites).
- **Practice**: topic quizzes (5 questions), timed chapter tests (10 questions, 10 minutes) and a
  "practise my mistakes" quiz. Questions are written by an LLM via OpenRouter the first time they are
  needed, saved, and reused. Answers and explanations are shown after submitting.
- **Feedback**: Helpful / Not helpful on every item (not helpful hides it), "Report this question"
  (never used again), and a confidence rating after each quiz. The Progress page shows accuracy per
  topic, topics to revise and quiz history.
- Syllabus data is in `backend/seed/syllabus.json` (2025-26). Check it against the CBSE curriculum
  each year.

## Keeping content safe

- YouTube search uses SafeSearch strict and the Education category only.
- Age-restricted videos and anything with a blocked term (`backend/seed/blocked_terms.txt`) in the
  title or description are never shown. Searches with blocked terms return nothing.
- Only YouTube's privacy-mode player can be embedded (Content-Security-Policy `frame-src`).
- AI-written questions can contain mistakes; reported questions are removed.
- External sites open in a new tab and are outside Study Hub's control. Also turn on device-level
  protection: Google Family Link or Microsoft Family Safety, YouTube Restricted Mode, and a family DNS
  filter on the home router (for example Cloudflare 1.1.1.3 or OpenDNS FamilyShield).
