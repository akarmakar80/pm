import os
import json
from contextlib import asynccontextmanager
from datetime import datetime, UTC
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

import db

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:3000")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_MODEL = "openai/gpt-oss-120b:free"


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(lifespan=lifespan)


class KanbanSaveRequest(BaseModel):
    user: str = "user"
    board: dict


class AiKanbanRequest(BaseModel):
    user: str = "user"
    user_message: str = ""
    board_state: dict


def _get_or_create_user(username: str) -> int:
    existing = db.get_user(username)
    if existing is not None:
        return existing["id"]
    return db.create_user(username, "password-hash-placeholder")


def _save_board(user_id: int, board: dict) -> int:
    data_json = json.dumps(board)
    existing_board = db.get_board_by_user(user_id)
    if existing_board is None:
        return db.create_board(user_id, data_json)
    board_id = existing_board["id"]
    db.update_board(board_id, data_json)
    db.add_board_update(board_id, json.dumps({"updated_at": datetime.now(UTC).isoformat()}))
    return board_id


@app.get("/api/ping")
def ping():
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/api/db-status")
def db_status():
    return {"db_path": db.get_db_path(), "users": db.count_users(), "boards": db.count_boards()}


@app.get("/api/kanban")
def get_kanban(user: str = "user"):
    user_id = _get_or_create_user(user)
    existing_board = db.get_board_by_user(user_id)
    if existing_board is None:
        initial = {
            "columns": [
                {"id": "col-backlog", "title": "Backlog", "cardIds": ["card-1", "card-2"]},
                {"id": "col-in-progress", "title": "In Progress", "cardIds": []},
                {"id": "col-review", "title": "Review", "cardIds": []},
                {"id": "col-done", "title": "Done", "cardIds": []},
                {"id": "col-blocked", "title": "Blocked", "cardIds": []},
            ],
            "cards": {
                "card-1": {"id": "card-1", "title": "Set up project", "details": "Initialize files and repo."},
                "card-2": {"id": "card-2", "title": "Create baseline UI", "details": "Add Kanban board components."},
            },
        }
        db.create_board(user_id, json.dumps(initial))
        return initial

    return json.loads(existing_board["data_json"])


@app.post("/api/kanban")
def post_kanban(payload: KanbanSaveRequest):
    user_id = _get_or_create_user(payload.user)
    board_id = _save_board(user_id, payload.board)
    return {"status": "ok", "board": payload.board, "board_id": board_id}


@app.get("/api/ai/ping")
def ai_ping():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"status": "ok", "value": 4, "note": "no key, local fallback"}

    try:
        resp = httpx.post(
            OPENROUTER_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": AI_MODEL,
                "messages": [{"role": "user", "content": "What is 2 + 2? Reply with just the number."}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"status": "ok", "value": content}
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)


@app.post("/api/ai/kanban")
def ai_kanban(request_data: AiKanbanRequest):
    key = os.getenv("OPENROUTER_API_KEY")

    if not key:
        return JSONResponse({"detail": "OPENROUTER_API_KEY not set"}, status_code=503)

    system_prompt = (
        "You are an AI assistant for a Kanban board app. "
        "The board JSON has: columns (array of {id, title, cardIds}) and cards (object of {id: {id, title, details}}). "
        "Respond ONLY with a JSON object in this exact format, no markdown, no extra text:\n"
        '{"text_response": "your reply to the user", "board_update": null}\n'
        "If the user wants to change the board, set board_update to the complete updated board object. "
        "Otherwise set board_update to null. "
        "When adding cards, generate a unique id like card-<random>. "
        "Keep titles and details concise."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Current board:\n{json.dumps(request_data.board_state, indent=2)}\n\nRequest: {request_data.user_message}",
        },
    ]

    try:
        resp = httpx.post(
            OPENROUTER_API_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": AI_MODEL, "messages": messages},
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)

    try:
        result = json.loads(content)
        text_response = result.get("text_response", content)
        board_update = result.get("board_update")
    except (json.JSONDecodeError, AttributeError):
        text_response = content
        board_update = None

    if board_update:
        user_id = _get_or_create_user(request_data.user)
        _save_board(user_id, board_update)

    return {"status": "ok", "text_response": text_response, "board_update": board_update}


@app.get("/{path:path}")
async def proxy_to_frontend(path: str, request: Request):
    if path.startswith("api"):
        return JSONResponse({"detail": "API endpoint not found"}, status_code=404)

    target_url = f"{FRONTEND_URL}/{path}" if path else f"{FRONTEND_URL}/"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(target_url)
        except httpx.RequestError:
            return PlainTextResponse("Frontend service unavailable", status_code=503)

    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "text/html"))
