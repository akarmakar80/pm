import json
import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app
import db


@pytest.fixture(autouse=True)
def temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    monkeypatch.setenv("KANBAN_DB_PATH", tmp.name)
    db.init_db()
    yield
    os.remove(tmp.name)


client = TestClient(app.app)


def test_ping():
    resp = client.get("/api/ping")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_db_status():
    resp = client.get("/api/db-status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["users"] == 0
    assert data["boards"] == 0


def test_kanban_get_and_post_flow():
    resp = client.get("/api/kanban?user=testuser")
    assert resp.status_code == 200
    board = resp.json()
    assert "columns" in board

    board["cards"]["card-x"] = {"id": "card-x", "title": "New", "details": "x"}
    board["columns"][0]["cardIds"].append("card-x")

    resp2 = client.post("/api/kanban", json={"user": "testuser", "board": board})
    assert resp2.status_code == 200
    resp3 = client.get("/api/kanban?user=testuser")
    assert resp3.status_code == 200
    assert "card-x" in resp3.json()["cards"]


def test_ai_ping_no_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    resp = client.get("/api/ai/ping")
    assert resp.status_code == 200
    assert resp.json()["value"] == 4


def test_ai_kanban_add_card():
    initial = client.get("/api/kanban?user=testuser").json()
    resp = client.post("/api/ai/kanban", json={"user": "testuser", "user_message": "Add card", "board_state": initial})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["board_update"] is not None
