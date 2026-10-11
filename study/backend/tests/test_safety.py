import json
from pathlib import Path

from safety import is_blocked
from test_app import RUBRIC, add_video, topic_id

SEED = Path(__file__).resolve().parent.parent / "seed"


def test_syllabus_terms_are_never_blocked():
    data = json.loads((SEED / "syllabus.json").read_text())
    for subject in data["subjects"]:
        for chapter in subject["chapters"]:
            for topic in chapter["topics"]:
                assert not is_blocked(f"{chapter['title']} {topic['title']} {topic['keywords']}"), topic


def test_blocked_terms():
    assert is_blocked("watch porn")
    assert is_blocked("Online BETTING tips")
    assert not is_blocked("seen with the naked eye")
    assert not is_blocked("sexual reproduction in flowering plants")


def test_blocked_search_returns_nothing_and_is_flagged(client, as_user):
    as_user("student")
    r = client.get("/api/search", params={"q": "nsfw videos"}).json()
    assert r == {"query": "nsfw videos", "outcome": "blocked", "topics": []}
    as_user("parent")
    assert client.get("/api/review/searches").json()[0]["outcome"] == "blocked"


def test_only_allowed_sites_can_be_added(client, as_user):
    as_user("educator")
    tid = topic_id(client, "ohms law")
    body = {**RUBRIC, "approve": True, "title": "Ohm's law notes", "type": "article",
            "url": "https://random-site.example.com/ohm", "topic_id": tid, "purpose": "reference"}
    r = client.post("/api/review/resources", json=body)
    assert r.status_code == 400 and "allowed sites" in r.json()["detail"]
    r = client.post("/api/review/resources", json={**body, "url": "https://www.udemy.com/course/physics-10/"})
    assert r.json()["status"] == "verified"
    r = client.post("/api/review/resources", json={**body, "url": "https://www.khanacademy.org/x", "title": "sexy physics"})
    assert r.status_code == 400


def test_sign_in_info_is_shown_on_items(client, as_user):
    as_user("educator")
    tid = topic_id(client, "ohms law")
    client.post("/api/review/resources", json={
        **RUBRIC, "approve": True, "title": "Physics course", "type": "course",
        "url": "https://www.udemy.com/course/physics-10/", "topic_id": tid, "purpose": "reference"})
    add_video(client, tid)
    as_user("student")
    pack = client.get(f"/api/topics/{tid}").json()
    udemy = next(i for i in pack["tabs"]["read"] if "udemy" in i["url"])
    assert udemy["platform"]["name"] == "Udemy"
    assert udemy["platform"]["login_url"].startswith("https://www.udemy.com/")
    assert pack["tabs"]["learn"][0]["platform"]["login_url"] is None


def test_only_parent_can_allow_new_sites(client, as_user):
    site = {"domain": "example-learning.in", "name": "Example Learning", "login_url": "https://example-learning.in/login"}
    as_user("educator")
    assert client.post("/api/review/platforms", json=site).status_code == 403
    as_user("parent")
    assert client.post("/api/review/platforms", json=site).status_code == 200
    as_user("student")
    assert "Example Learning" in [p["name"] for p in client.get("/api/platforms").json()]
