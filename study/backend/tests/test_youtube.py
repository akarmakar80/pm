import httpx

import youtube

VIDEOS = [
    # id, title, channel, duration, embeddable, age_restricted
    ("vid00000001", "Ohm's Law Class 10 explained", "Some Teacher", "PT14M", True, False),
    ("vid00000002", "Ohm's law numericals solved", "Magnet Brains", "PT12M", True, False),
    ("vid00000003", "Ohm's law Class 9", "Some Teacher", "PT20M", True, False),
    ("vid00000004", "Ohm's law #shorts", "Some Teacher", "PT40S", True, False),
    ("vid00000005", "Ohm's law lecture", "Some Teacher", "PT12M", False, False),
    ("vid00000006", "Ohm's law experiment", "Some Teacher", "PT12M", True, True),
    ("vid00000007", "Ohm's law sexy trick", "Some Teacher", "PT12M", True, False),
]
seen = {}


def fake_api(request: httpx.Request) -> httpx.Response:
    path = request.url.path.rsplit("/", 1)[-1]
    if path == "search":
        seen.update(request.url.params)
        return httpx.Response(200, json={"items": [{"id": {"videoId": v[0]}} for v in VIDEOS]})
    return httpx.Response(200, json={"items": [{
        "id": vid,
        "snippet": {"title": title, "channelTitle": channel, "publishedAt": "2024-06-01T10:00:00Z", "description": ""},
        "contentDetails": {"duration": duration} | ({"contentRating": {"ytRating": "ytAgeRestricted"}} if age else {}),
        "statistics": {"viewCount": "250000", "likeCount": "8000", "commentCount": "400"},
        "status": {"embeddable": embeddable},
    } for vid, title, channel, duration, embeddable, age in VIDEOS]})


def test_find_videos_filters_and_ranks():
    with httpx.Client(transport=httpx.MockTransport(fake_api)) as client:
        videos = youtube.find_videos(client, "key", "Ohm's law class 10")
    assert [v["video_id"] for v in videos] == ["vid00000002", "vid00000001"]  # trusted channel ranks first
    assert videos[0]["purpose"] == "examples" and videos[1]["purpose"] == "concept"
    assert seen["safeSearch"] == "strict" and seen["videoCategoryId"] == "27" and seen["videoEmbeddable"] == "true"


def test_parse_duration():
    assert youtube.parse_duration("PT1H2M3S") == 3723
