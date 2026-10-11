RUBRIC = {"alignment": 4, "accuracy": 5, "clarity": 4, "examples": 4, "age_fit": 5}


def topic_id(client, query):
    r = client.get("/api/search", params={"q": query}).json()
    assert r["outcome"] == "match", r
    return r["topics"][0]["id"]


def all_items(pack):
    return [i for tab in pack["tabs"].values() for i in tab]


def add_video(client, tid, approve=True, **rubric):
    return client.post("/api/review/resources", json={
        **RUBRIC, **rubric, "approve": approve, "title": "Ohm's law explained", "type": "video",
        "url": "https://www.youtube.com/watch?v=abcdefghijk", "topic_id": tid, "purpose": "concept",
        "recommendation": "Clear experiment-based explanation",
    })


def test_login_required(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"username": "student", "password": "x"}).status_code == 401


def test_login_and_roles(client, as_user):
    assert as_user("student")["role"] == "student"
    assert client.get("/api/review/queue").status_code == 403
    as_user("educator")
    assert client.get("/api/review/queue").status_code == 200


def test_search_outcomes_are_logged(client, as_user):
    as_user("student")
    assert client.get("/api/search", params={"q": "how plants make food"}).json()["topics"][0]["title"] == "Nutrition"
    assert client.get("/api/search", params={"q": "refraction"}).json()["outcome"] == "choose"
    assert client.get("/api/search", params={"q": "football"}).json()["outcome"] == "out_of_syllabus"
    as_user("parent")
    outcomes = [s["outcome"] for s in client.get("/api/review/searches").json()]
    assert outcomes == ["out_of_syllabus", "choose", "match"]


def test_topic_pack_structure_and_library(client, as_user):
    as_user("student")
    tid = topic_id(client, "ohms law")
    pack = client.get(f"/api/topics/{tid}").json()
    assert pack["chapter_title"] == "Electricity"
    assert {i["title"] for i in pack["tabs"]["explore"]} == {"Ohm's Law", "Resistance in a Wire"}
    assert pack["tabs"]["read"][0]["badge"] == "NCERT"
    assert pack["tabs"]["practice"][0]["url"].endswith("jesc111.pdf")
    client.get(f"/api/topics/{tid}")
    library = client.get("/api/library").json()
    assert [(e["id"], e["open_count"]) for e in library] == [(tid, 2)]


def test_reviewed_video_becomes_visible_with_educator_badge(client, as_user):
    as_user("educator")
    tid = topic_id(client, "ohms law")
    assert add_video(client, tid).json()["status"] == "verified"
    as_user("student")
    learn = client.get(f"/api/topics/{tid}").json()["tabs"]["learn"]
    assert learn[0]["video_id"] == "abcdefghijk"
    assert learn[0]["badge"] == "Verified by Educator"
    assert learn[0]["recommendation"] == "Clear experiment-based explanation"


def test_approval_needs_minimum_scores(client, as_user):
    as_user("educator")
    tid = topic_id(client, "ohms law")
    assert add_video(client, tid, accuracy=2).status_code == 400


def test_rejected_and_reported_items_are_hidden(client, as_user):
    as_user("educator")
    tid = topic_id(client, "ohms law")
    rejected = add_video(client, tid, approve=False, accuracy=2).json()
    assert rejected["status"] == "rejected"

    as_user("student")
    pack = client.get(f"/api/topics/{tid}").json()
    assert rejected["id"] not in [i["id"] for i in all_items(pack)]
    sim = pack["tabs"]["explore"][0]
    client.post(f"/api/resources/{sim['id']}/report", json={"note": "link broken"})
    pack = client.get(f"/api/topics/{tid}").json()
    assert sim["id"] not in [i["id"] for i in all_items(pack)]

    as_user("educator")
    queue = client.get("/api/review/queue").json()
    assert queue[0]["id"] == sim["id"] and queue[0]["reports"] == "link broken"
    client.post(f"/api/review/resources/{sim['id']}", json={**RUBRIC, "approve": True})
    as_user("student")
    assert sim["id"] in [i["id"] for i in client.get(f"/api/topics/{tid}").json()["tabs"]["explore"]]


def test_add_channel_requires_api_key(client, as_user):
    as_user("parent")
    assert client.post("/api/review/sources", json={"handle": "@ncert"}).status_code == 400
