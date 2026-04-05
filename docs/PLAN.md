# High level steps for project

Part 1: Plan

- Create and confirm project-level AGENTS.md and frontend/AGENTS.md.
- Review existing frontend MVP code and existing tests.
- Add explicit checklist and success criteria per part.
- Confirm with user before proceeding.

Success criteria:
- `docs/PLAN.md` and `frontend/AGENTS.md` exist and are approved.
- high-level tasks are split into subtasks with OKRs.
- user gives go-ahead to move to Part 2.

Part 2: Scaffolding (Docker + FastAPI + hello world)

- Create `Dockerfile` and `docker-compose.yml` in root.
- Add backend dependencies: `fastapi`, `uvicorn`, `databases`, `sqlalchemy` (as needed), `python-dotenv`, `httpx`.
- Implement backend structure in `backend/app.py` with:
  - GET `/` returning simple HTML "hello world"
  - GET `/api/ping` returning JSON `{status: "ok", time: ...}`
- Add start/stop scripts:
  - `scripts/start.ps1`, `scripts/stop.ps1`, `scripts/start.sh`, `scripts/stop.sh`.
- Validate container startup and route response.
- Add smoke test script in `backend/test_smoke.py` to call `/api/ping`.

Success criteria:
- `docker-compose up --build` starts both backend and static site container.
- `/api/ping` responds with 200 and JSON payload.
- `scripts/start*` and `scripts/stop*` work.
- a CI task can run backend smoke test.

Part 3: Add in Frontend static build and serve

- Integrate existing frontend into full deployment:
  - Build Next.js output to `frontend/.next` and static export if needed.
  - Backend serves frontend by mounting static files or reverse proxy.
- Ensure root route `/` serves the app, showing current Kanban demo.
- Add test targets:
  - `npm test`, `npm run lint`, and `npm run build` from frontend.
  - integration test hitting `/` and verifying expected DOM text.

Success criteria:
- `docker-compose up --build` exposes app at `/` with Kanban.
- frontend tests pass in local run.

Part 4: Fake sign-in experience

- Add auth in frontend only with state + localStorage:
  - page shows login form when not signed in.
  - checking hardcoded credentials `user` / `password`.
  - on success, show board + sign-out button.
- Keep backend unchanged (API open for now).
- Add end-to-end tests for login flow, logout, invalid credentials.

Success criteria:
- login with correct creds shows board.
- invalid login shows error message.
- logout returns to login screen.

Part 5: Database modeling

- Define schema:
  - users: id, username, password_hash, created_at
  - boards: id, user_id, data_json, updated_at
  - board_updates (optional): id, board_id, diff_json, created_at
- Pick SQLite local file `data/kanban.db`.
- Add docs in `docs/DB_SCHEMA.md` and update `docs/PLAN.md`.
- Write unit tests validating ORM models and JSON save/load.

Success criteria:
- DB schema file exists.
- migrations or create-if-not-exist are implemented.
- tests verify row insert and kanban JSON retrieval.

Part 6: Backend API

- Implement backend endpoints:
  - GET `/api/kanban` (user from basic auth header session cookie for MVP non-secure; can use query string user='user').
  - POST `/api/kanban` with JSON payload to update board.
  - GET `/api/health` and `/api/ping`.
- Use SQLite with ORM or raw queries.
- Add tests: backend fastapi test client for endpoints.

Success criteria:
- GET `/api/kanban` returns canonical board JSON.
- POST updates persisted board.

Part 7: Frontend + Backend integration

- Replace frontend local state with backend calls:
  - load board via `/api/kanban` after login.
  - on card move/edit/create send updates to POST `/api/kanban`.
- Add optimistic UI updates and revert errors.
- Add full integration tests for API flow (Playwright or Vitest with mock server).

Success criteria:
- board persistence between reloads.
- drag/drop and edit operations persist.

Part 8: AI connectivity

- Add backend AI service component using OpenRouter API key.
- Route: POST `/api/ai/ping` calls OpenRouter to evaluate prompt "2+2".
- Accept env var `OPENROUTER_API_KEY`.
- Add tests with mocking (pytest + respx) and real optional integration.

Success criteria:
- AI route returns a valid response.
- tests cover 2+2 call.

Part 9: AI structured board updates

- Add route POST `/api/ai/kanban` with body containing
  - `user_message`.
  - `board_state`.
  - optionally `conversation_history`.
- Server sends request to OpenRouter with full context.
- LLM response parser returns:
  - `text_response`
  - `board_update` nullable (change set or full board JSON)
- If provided, backend applies update and persists.
- Response includes both text and updated board state.
- Add tests for parser and route.

Success criteria:
- backend applies AI updates correctly when returned.
- if no update, board unchanged.

Part 10: UI AI chat widget

- Add sidebar chat UI:
  - messages list
  - input box
  - “send” button
  - history tracking.
- On send, call `/api/ai/kanban`.
- Render text from AI and apply board updates.
- Add tests on UI and API interactions.

Success criteria:
- chat can ask questions and AI responses appear.
- if AI returns updates, board UI refreshes.

## General test strategy

- Unit tests in `frontend/src/**/*.{test.tsx,test.ts}` and `backend/tests`.
- Integration tests via Playwright in `tests/` for key flows.
- CI should run `npm ci`, `npm test` and Python test suite, and container smoke tests.
