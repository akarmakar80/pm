import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDY_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    from app import app

    with TestClient(app) as c:
        yield c


def login(client, username):
    client.cookies.clear()
    r = client.post("/api/auth/login", json={"username": username, "password": username})
    assert r.status_code == 200
    return r.json()


@pytest.fixture
def as_user(client):
    return lambda username: login(client, username)
