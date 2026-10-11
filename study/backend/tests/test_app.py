import youtube
from conftest import topic_id

VIDEOS = [
    {"video_id": f"vid0000000{i}", "title": title, "channel": "Magnet Brains", "duration_sec": 900,
     "score": 0.9 - i / 10, "purpose": purpose}
    for i, (title, purpose) in enumerate([
        ("Ohm's law explained", "concept"),
        ("Ohm's law numericals solved", "examples"),
        ("Ohm's law in daily life", "application"),
    ])
]


def test_search_outcomes(client):
    assert client.get("/api/search", params={"q": "how plants make food"}).json()["topics"][0]["title"] == "Nutrition"
    assert client.get("/api/search", params={"q": "refraction"}).json()["outcome"] == "choose"
    assert client.get("/api/search", params={"q": "football"}).json()["outcome"] == "out_of_syllabus"
    assert client.get("/api/search", params={"q": "nsfw videos"}).json() == {
        "query": "nsfw videos", "outcome": "blocked", "topics": []}


def test_topic_pack_without_youtube_key(client):
    tid = topic_id(client, "ohms law")
    pack = client.get(f"/api/topics/{tid}").json()
    assert pack["videos_enabled"] is False and pack["tabs"]["learn"] == []
    assert {i["title"] for i in pack["tabs"]["explore"]} == {"Ohm's Law", "Resistance in a Wire"}
    assert pack["tabs"]["practice"][0]["url"].endswith("jesc111.pdf")
    client.get(f"/api/topics/{tid}")
    assert [(e["id"], e["open_count"]) for e in client.get("/api/library").json()] == [(tid, 2)]


def test_videos_are_found_once_and_saved(client, monkeypatch):
    calls = []
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    monkeypatch.setattr(youtube, "find_videos", lambda client, key, query: calls.append(query) or VIDEOS)
    tid = topic_id(client, "ohms law")
    learn = client.get(f"/api/topics/{tid}").json()["tabs"]["learn"]
    assert [v["purpose"] for v in learn] == ["concept", "examples", "application"]
    assert learn[0]["provider"] == "Magnet Brains" and learn[0]["platform"]["name"] == "YouTube"
    client.get(f"/api/topics/{tid}")
    assert calls == ["Ohm's Law and Resistance class 10 Science CBSE NCERT"]


def test_rating_reorders_and_hides(client, monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "key")
    monkeypatch.setattr(youtube, "find_videos", lambda *a: VIDEOS[:1] + [VIDEOS[0] | {"video_id": "vid00000009", "score": 0.1}])
    tid = topic_id(client, "ohms law")
    first, second = client.get(f"/api/topics/{tid}").json()["tabs"]["learn"]
    client.post(f"/api/resources/{second['id']}/rating", json={"helpful": True})
    assert client.get(f"/api/topics/{tid}").json()["tabs"]["learn"][0]["id"] == second["id"]
    client.post(f"/api/resources/{first['id']}/rating", json={"helpful": False})
    assert [v["id"] for v in client.get(f"/api/topics/{tid}").json()["tabs"]["learn"]] == [second["id"]]


def test_sign_in_info_on_items(client):
    tid = topic_id(client, "quadratic formula")
    khan = next(i for i in client.get(f"/api/topics/{tid}").json()["tabs"]["read"] if i["provider"] == "Khan Academy")
    assert khan["platform"]["login_url"] == "https://www.khanacademy.org/login"
