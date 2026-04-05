# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Kanban project management web app. NextJS frontend + Python FastAPI backend, packaged in Docker. The backend proxies all non-API routes to the frontend container.

MVP credentials: `user` / `password` (hardcoded in frontend auth, no real auth backend).

## Architecture

- `frontend/` — Next.js 16 app (React 19, Tailwind 4, dnd-kit for drag-and-drop)
- `backend/` — FastAPI app (`app.py`) with SQLite persistence (`db.py`)
- `data/kanban.db` — SQLite database, auto-created on backend startup
- `docker-compose.yml` — two services: `frontend` (port 3000) and `backend` (port 8000)
- Backend proxies `/*` (non-API) to the frontend container at `http://frontend:3000`

### Key data flow
Board state is stored as a single JSON blob in `boards.data_json`. The `board_updates` table logs every write. The AI endpoint (`POST /api/ai/kanban`) receives `user_message` + `board_state`, and optionally returns a `board_update` that the backend persists.

### Environment
- `OPENROUTER_API_KEY` — in `.env` at project root; loaded by Docker
- `KANBAN_DB_PATH` — optional override for SQLite path (default: `data/kanban.db`)
- AI model: `openai/gpt-oss-120b:free` via OpenRouter

## Commands

### Docker (primary way to run)
```bash
# Start
scripts/start.sh        # Linux/Mac
scripts/start.ps1       # Windows PowerShell

# Stop
scripts/stop.sh
scripts/stop.ps1
```

### Backend (local dev)
```bash
cd backend
pip install -r requirements.txt      # or: uv pip install -r requirements.txt
uvicorn app:app --reload --port 8000

# Run backend unit tests
pytest tests/

# Smoke test (requires running server)
python test_smoke.py
```

### Frontend (local dev)
```bash
cd frontend
npm ci
npm run dev             # dev server on :3000
npm run build           # production build
npm run lint
npm run test            # vitest unit tests (run once)
npm run test:unit:watch # vitest watch mode
npm run test:e2e        # Playwright e2e tests
npm run test:all        # unit + e2e
```

## Coding Standards

From AGENTS.md — these apply to all code in this repo:

1. Use latest library versions and idiomatic patterns
2. Keep it simple — never over-engineer, no unnecessary defensive programming, no extra features
3. Be concise — no emojis, ever
4. When debugging: identify root cause with evidence before fixing; do not guess
