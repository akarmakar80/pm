import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDY_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from app import app

    with TestClient(app) as c:
        yield c


def topic_id(client, query):
    r = client.get("/api/search", params={"q": query}).json()
    assert r["outcome"] == "match", r
    return r["topics"][0]["id"]
