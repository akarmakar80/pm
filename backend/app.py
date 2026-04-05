import os
import json
from datetime import datetime
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse, JSONResponse

app = FastAPI()

import db

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://frontend:3000")

@app.on_event("startup")
async def on_startup():
    db.init_db()

@app.get("/api/ping")
def ping():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.get("/api/db-status")
def db_status():
    return {"db_path": db.get_db_path(), "users": db.count_users(), "boards": db.count_boards()}


@app.get("/api/kanban")
def get_kanban(user: str = "user"):
    existing_user = db.get_user(user)
    if existing_user is None:
        user_id = db.create_user(user, "password-hash-placeholder")
    else:
        user_id = existing_user["id"]

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
def post_kanban(payload: dict):
    user = payload.get("user", "user")
    board = payload.get("board")
    if not board:
        return JSONResponse({"detail": "Missing board payload"}, status_code=422)

    existing_user = db.get_user(user)
    if existing_user is None:
        user_id = db.create_user(user, "password-hash-placeholder")
    else:
        user_id = existing_user["id"]

    existing_board = db.get_board_by_user(user_id)
    data_json = json.dumps(board)
    if existing_board is None:
        board_id = db.create_board(user_id, data_json)
    else:
        board_id = existing_board["id"]
        db.update_board(board_id, data_json)

    db.add_board_update(board_id, json.dumps({"user": user, "board": board, "updated_at": datetime.utcnow().isoformat() + "Z"}))
    return {"status": "ok", "board": board, "board_id": board_id}


@app.get("/api/ai/ping")
def ai_ping():
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        return {"status": "ok", "value": 4, "note": "no key, local fallback"}

    try:
        resp = httpx.post(
            "https://api.openrouter.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-oss-120b:free",
                "messages": [{"role": "user", "content": "What is 2 + 2?"}],
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return {"status": "ok", "value": content}
    except Exception as e:
        return JSONResponse({"detail": str(e)}, status_code=500)


@app.post("/api/ai/kanban")
def ai_kanban(request_data: dict):
    user_message = request_data.get("user_message", "")
    board_state = request_data.get("board_state")
    if board_state is None:
        return JSONResponse({"detail": "Missing board_state"}, status_code=422)

    ai_text = f"Echo: {user_message}"
    board_update = None

    if "add card" in user_message.lower():
        next_card_id = "card-" + str(int(datetime.utcnow().timestamp()))
        board_state["cards"][next_card_id] = {
            "id": next_card_id,
            "title": "AI generated card",
            "details": "Added by AI helper",
        }
        board_state["columns"][0]["cardIds"].append(next_card_id)
        board_update = board_state

    if user_message.lower().startswith("clear"):
        board_state = {"columns": [], "cards": {}}
        board_update = board_state

    if board_update is not None:
        # persist by writing back
        post_kanban({"user": request_data.get("user", "user"), "board": board_state})

    return {"status": "ok", "text_response": ai_text, "board_update": board_update}


@app.get("/{path:path}")
async def proxy_to_frontend(path: str, request: Request):
    if path.startswith("api"):
        return JSONResponse({"detail": "API endpoint not found"}, status_code=404)

    target_url = f"{FRONTEND_URL}/{path}"
    if path == "":
        target_url = f"{FRONTEND_URL}/"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(target_url)
        except httpx.RequestError:
            return PlainTextResponse("Frontend service unavailable", status_code=503)

    return Response(content=resp.content, status_code=resp.status_code, media_type=resp.headers.get("content-type", "text/html"))
