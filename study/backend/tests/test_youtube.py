import httpx

import youtube
from db import connect

VIDEOS = [
    # id, title, duration, embeddable
    ("vid00000001", "Ohm's Law Class 10 Physics | Resistance explained", "PT14M", True),
    ("vid00000002", "Ohm's law numericals solved examples", "PT9M30S", True),
    ("vid00000003", "Motion Class 9 Physics", "PT20M", True),
    ("vid00000004", "Ohm's law in 30 seconds #shorts", "PT30S", True),
    ("vid00000005", "Funny vlog from our trip", "PT10M", True),
    ("vid00000006", "Refraction through glass slab", "PT12M", False),
    ("vid00000007", "Ohm's law resistance experiment", "PT12M", True),
    ("vid00000008", "Ohm's law trick sexy teacher", "PT12M", True),
]
AGE_RESTRICTED = {"vid00000007"}


def fake_api(request: httpx.Request) -> httpx.Response:
    path = request.url.path.rsplit("/", 1)[-1]
    if path == "channels":
        return httpx.Response(200, json={"items": [{
            "id": "UCtest", "snippet": {"title": "Test Channel"},
            "contentDetails": {"relatedPlaylists": {"uploads": "UUtest"}},
        }]})
    if path == "playlistItems":
        return httpx.Response(200, json={"items": [{"contentDetails": {"videoId": v[0]}} for v in VIDEOS]})
    if path == "videos":
        return httpx.Response(200, json={"items": [{
            "id": vid,
            "snippet": {"title": title, "publishedAt": "2024-06-01T10:00:00Z"},
            "contentDetails": {"duration": duration} | (
                {"contentRating": {"ytRating": "ytAgeRestricted"}} if vid in AGE_RESTRICTED else {}),
            "statistics": {"viewCount": "250000", "likeCount": "8000", "commentCount": "400"},
            "status": {"embeddable": embeddable},
        } for vid, title, duration, embeddable in VIDEOS]})
    raise AssertionError(path)


def test_parse_duration():
    assert youtube.parse_duration("PT1H2M3S") == 3723
    assert youtube.parse_duration("PT45S") == 45


def test_index_channel_adds_on_syllabus_candidates(client, as_user):
    conn = connect()
    source_id = conn.execute(
        "INSERT INTO sources (kind, name, external_id, tier) VALUES ('youtube_channel', 'Test Channel', 'UCtest', 3)"
    ).lastrowid
    source = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    with httpx.Client(transport=httpx.MockTransport(fake_api)) as http:
        assert youtube.index_channel(conn, http, "key", source) == 2
        assert youtube.index_channel(conn, http, "key", source) == 0  # no duplicates
    conn.commit()

    rows = conn.execute(
        "SELECT r.video_id, r.status, rt.purpose, t.title FROM resources r"
        " JOIN resource_topics rt ON rt.resource_id = r.id JOIN topics t ON t.id = rt.topic_id"
        " WHERE r.source_id = ? ORDER BY r.video_id",
        (source_id,),
    ).fetchall()
    assert [tuple(r) for r in rows] == [
        ("vid00000001", "candidate", "concept", "Ohm's Law and Resistance"),
        ("vid00000002", "candidate", "examples", "Ohm's Law and Resistance"),
    ]
    conn.close()

    as_user("student")
    tid = client.get("/api/search", params={"q": "ohms law"}).json()["topics"][0]["id"]
    assert client.get(f"/api/topics/{tid}").json()["tabs"]["learn"] == []
    as_user("educator")
    assert {q["video_id"] for q in client.get("/api/review/queue").json()} == {"vid00000001", "vid00000002"}
