# Code Review

Reviewed: 2026-04-05  
Scope: All source files in `backend/`, `frontend/src/`, `frontend/tests/`, `Dockerfile`, `docker-compose.yml`

---

## High

### H1 — Playwright e2e tests bypass the backend entirely

**Files**: `frontend/playwright.config.ts:10`, `frontend/tests/kanban.spec.ts`

`playwright.config.ts` sets `baseURL: "http://127.0.0.1:3000"`, which is the raw Next.js dev server. The `/api/*` routes only exist on the FastAPI backend at port 8000. When `KanbanBoard` calls `fetch("/api/kanban")` during e2e tests, the request fails with a 404 or connection error. The component silently falls back to `initialData` from `kanban.ts`. The tests pass — but against local fallback data, never through the real backend stack.

**Fix**: Change `baseURL` to `http://localhost:8000` (the Docker backend port) and remove the `webServer` block (the server is brought up separately). Or, if running locally without Docker, start the FastAPI dev server and point Playwright at it.

---

### H2 — Column IDs are inconsistent between frontend and backend

**Files**: `frontend/src/lib/kanban.ts:20-29`, `backend/app.py:40-49`

The frontend's `initialData` (used as fallback) defines columns with IDs `col-backlog`, `col-discovery`, `col-progress`, `col-review`, `col-done`. The backend creates new boards with `col-backlog`, `col-in-progress`, `col-review`, `col-done`, `col-blocked`. Two columns differ (`col-discovery`/`col-progress` vs `col-in-progress`/`col-blocked`), and the column count matches by coincidence.

Consequences:
- A user accessing via port 8000 gets backend-seeded columns; a user who ever falls back to `initialData` gets different columns with different IDs. Cards moved between them would reference IDs that don't exist in the other schema.
- The Playwright test at line 31 checks for `column-col-discovery` — a column that only exists in the frontend fallback, not in any real persisted board.

**Fix**: Make `initialData` in `kanban.ts` match the backend's initial board exactly (same column IDs, same titles). Since the backend is authoritative, update `kanban.ts`. Remove `initialData` as a fallback for the loaded board — if the API fails, show an error; don't silently render stale local data.

---

### H3 — `saveBoard` errors are silently swallowed

**Files**: `frontend/src/components/KanbanBoard.tsx:51-68`

`saveBoard()` is called as a fire-and-forget inside `setAndSave`. The async function runs but its rejection is never caught:

```typescript
const setAndSave = (updater: ...) => {
  setBoard((prev) => {
    const next = updater(prev);
    saveBoard(next);   // promise not caught
    return next;
  });
};
```

`saveBoard` itself does catch and call `setError`, so the error surface is not zero — but only for the error ref in that closure. If a network error occurs mid-save, the user sees the card appear to move and no feedback.

**Fix**: Move `saveBoard` out of the `setBoard` updater. Call it after `setBoard` and `.catch()` the promise:

```typescript
const setAndSave = (updater: ...) => {
  setBoard((prev) => {
    const next = updater(prev);
    return next;
  });
  setBoard((next) => { saveBoard(next).catch(...); return next; });
};
```

Or better: maintain a pending-save ref and drain it with a useEffect.

---

### H4 — Logged-in username is never passed to API calls

**Files**: `frontend/src/app/auth/page.tsx`, `frontend/src/components/KanbanBoard.tsx:36,56`

`auth/page.tsx` hardcodes credentials to `user`/`password` but never communicates the username downward. `KanbanBoard` independently hardcodes `user: "user"` in every fetch. These happen to agree but the auth layer and the data layer are not connected — if you ever rename the user or add a real login, the board fetch will silently keep using `"user"`.

**Fix**: Pass `username` as a prop from `AuthPage` → `KanbanBoard`, and use it in all API calls. Even for the MVP, threading this now prevents a larger refactor later.

---

## Medium

### M1 — AI endpoint is a stub; OpenRouter is never called

**File**: `backend/app.py:106-134`

`POST /api/ai/kanban` implements two hardcoded keyword matches (`"add card"`, `"clear"`) and returns an echo string. The OpenRouter API key in `.env` and the `httpx` dependency are never used here. The `GET /api/ai/ping` does call OpenRouter, but the main chat endpoint does not.

This means the AI chat widget in the UI is functionally a no-op except for those two keywords.

**Action**: Either implement the real LLM call (Part 9 of PLAN.md — still incomplete), or mark it clearly as a stub in code comments so future work isn't surprised.

---

### M2 — Backend uses deprecated FastAPI and datetime APIs

**File**: `backend/app.py:14`, `backend/app.py:20,78,117`, `backend/db.py:70,84,98,139`

Two deprecation warnings fire on every test run:
1. `@app.on_event("startup")` — deprecated since FastAPI 0.93; replace with `lifespan` context manager.
2. `datetime.utcnow()` — deprecated since Python 3.12; replace with `datetime.now(datetime.UTC)`.

These are not breaking today but will be in future Python/FastAPI versions.

**Fix**:

```python
# app.py — replace on_event
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield

app = FastAPI(lifespan=lifespan)
```

```python
# everywhere datetime.utcnow() is used
from datetime import datetime, UTC
datetime.now(UTC).isoformat()
```

---

### M3 — Backend endpoint accepts raw `dict` with no validation

**File**: `backend/app.py:57-79`

`POST /api/kanban` accepts `payload: dict`. Malformed payloads (missing keys, wrong types) return either a 422 from FastAPI's generic dict handler or a silent `None` value. No Pydantic model means no automatic validation, no OpenAPI schema, and no IDE support.

**Fix**: Define Pydantic models:

```python
from pydantic import BaseModel

class KanbanSaveRequest(BaseModel):
    user: str = "user"
    board: dict  # or a typed BoardData model

@app.post("/api/kanban")
def post_kanban(payload: KanbanSaveRequest): ...
```

Same applies to `POST /api/ai/kanban`.

---

### M4 — `ai_kanban` calls `post_kanban()` as an internal function

**File**: `backend/app.py:132`

```python
post_kanban({"user": request_data.get("user", "user"), "board": board_state})
```

This calls the endpoint handler directly with a raw dict, bypassing FastAPI's request parsing. If `post_kanban`'s signature ever changes to use Pydantic models (see M3), this call breaks silently.

**Fix**: Call the `db.*` functions directly instead of routing through the endpoint.

---

### M5 — `db.py` creates the data directory twice

**File**: `backend/db.py:14-15,19-20`

```python
# At module import time (lines 14-15)
default_db = get_db_path()
(Path(default_db).parent).mkdir(parents=True, exist_ok=True)

# Again inside every get_connection() call (lines 19-20)
(Path(db_path).parent).mkdir(parents=True, exist_ok=True)
```

The module-level code also only creates the directory for the *default* path, not for whatever `KANBAN_DB_PATH` is set to. If the env var is set to a different path, only `get_connection()` creates it.

**Fix**: Remove lines 14-15. `get_connection()` already handles it correctly.

---

## Low

### L1 — Frontend `initialData` is used as fallback masking backend errors

**File**: `frontend/src/components/KanbanBoard.tsx:37-47`

```typescript
} catch (err) {
  setError(err instanceof Error ? err.message : String(err));
  setBoard(initialData);  // silently shows stale placeholder data
}
```

The error is set, but the board is also populated with placeholder data. A user who sees an error banner might still interact with a functional-looking (but locally-stored, non-persisted) board and lose their changes.

**Fix**: On load failure, show the error and leave the board empty. Don't populate with `initialData`.

---

### L2 — `db.create_user` doesn't handle UNIQUE constraint violations

**File**: `backend/db.py:69-80`

`sqlite3.IntegrityError` is raised if `username` already exists. It propagates unhandled as a 500 from FastAPI. Currently this is masked because `app.py` calls `get_user` first, but if two concurrent requests race, both could pass the `get_user` check and one will throw.

**Fix**: Catch `sqlite3.IntegrityError` in `create_user` and re-raise as a structured application error, or use `INSERT OR IGNORE` and return the existing user ID.

---

### L3 — Card drag-and-drop spreads `{...listeners}` onto the article element

**File**: `frontend/src/components/KanbanCard.tsx:31`

The `{...listeners}` from `useSortable` attaches pointer event handlers directly to the `<article>`. The delete and move-left/move-right buttons inside that article will fire the drag listener on click before their own `onClick`. The `activationConstraint: { distance: 6 }` in `KanbanBoard.tsx` mitigates this, but button clicks that don't move the pointer 6px still briefly engage the drag sensor.

**Fix**: Use a dedicated drag handle element and spread `{...listeners}` only on that, keeping the action buttons outside the drag target.

---

### L4 — No `OPENROUTER_API_KEY` in `docker-compose.yml`

**File**: `docker-compose.yml:14-15`

The `.env` file contains `OPENROUTER_API_KEY` but `docker-compose.yml` only passes `PYTHONUNBUFFERED=1`. The key is never injected into the container, so `os.getenv("OPENROUTER_API_KEY")` returns `None` at runtime.

**Fix**: Add to the backend environment block:
```yaml
environment:
  - PYTHONUNBUFFERED=1
  - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
```
And add an `env_file: .env` directive, or explicitly list the variable.

---

### L5 — `KanbanBoard` re-renders `cardsById` memo unnecessarily

**File**: `frontend/src/components/KanbanBoard.tsx:77`

```typescript
const cardsById = useMemo(() => board.cards, [board.cards]);
```

`board.cards` is already the object reference. `useMemo` with a single dependency that is the return value itself adds no value — it's equivalent to `const cardsById = board.cards`. Remove the memo.

---

## Not Issues (confirming these are correct)

- **`vi` not imported in test files** — `vitest.config.ts` sets `globals: true`; `vi` is available globally. Not a bug.
- **`.env` committed to git** — `.gitignore` line 130 excludes `.env`. File is not tracked.
- **No CORS middleware** — backend proxies the frontend, so browser requests go to one origin (port 8000). CORS is not needed for this architecture.
- **Frontend-only auth (no backend session)** — explicitly scoped to MVP per `AGENTS.md`.
