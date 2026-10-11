"""Find the best YouTube videos for a syllabus topic.

Searches only YouTube's Education category with SafeSearch on, then drops anything age-restricted,
not embeddable, too short, about another class, or containing blocked words. The rest are ranked
by views, engagement, length and recency, with a boost for well-known CBSE channels.
"""

import math
import re
from datetime import UTC, datetime

import httpx

from safety import is_blocked

API = "https://www.googleapis.com/youtube/v3"
EDUCATION_CATEGORY = "27"
OTHER_CLASS = re.compile(r"\b(class|std|grade)\s*-?\s*(6|7|8|9|11|12)(th)?\b", re.IGNORECASE)
MIN_DURATION_SEC = 180
MAX_DURATION_SEC = 2 * 3600
TRUSTED_CHANNELS = (
    "ncert", "ciet", "khan academy", "magnet brains", "learnohub", "physics wallah", "vedantu",
    "infinity learn", "dear sir", "byju", "unacademy", "exam fear", "shobhit nirwan", "doubtnut",
)


def parse_duration(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    days, hours, minutes, seconds = (int(g or 0) for g in m.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def guess_purpose(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ("real life", "daily life", "application", "in everyday", "practical", "activity")):
        return "application"
    if any(w in t for w in ("example", "solved", "solution", "exercise", "questions", "numerical", "pyq")):
        return "examples"
    return "concept"


def unsafe(video: dict) -> bool:
    return (
        video["contentDetails"].get("contentRating", {}).get("ytRating") == "ytAgeRestricted"
        or not video["status"].get("embeddable", False)
        or is_blocked(f"{video['snippet']['title']} {video['snippet'].get('description', '')}")
    )


def score(video: dict, duration_sec: int) -> float:
    stats = video.get("statistics", {})
    views = int(stats.get("viewCount", 0))
    engagement = (int(stats.get("likeCount", 0)) + 2 * int(stats.get("commentCount", 0))) / max(views, 1)
    published = datetime.fromisoformat(video["snippet"]["publishedAt"].replace("Z", "+00:00"))
    recency = max(0.0, 1 - (datetime.now(UTC) - published).days / 365 / 6)
    trusted = any(c in video["snippet"]["channelTitle"].lower() for c in TRUSTED_CHANNELS)
    return round(
        0.35 * min(math.log10(views + 1) / 7, 1)
        + 0.25 * min(engagement * 20, 1)
        + 0.10 * (1.0 if 360 <= duration_sec <= 1800 else 0.5)
        + 0.10 * recency
        + 0.20 * trusted,
        4,
    )


def find_videos(client: httpx.Client, api_key: str, query: str, limit: int = 8) -> list[dict]:
    """Search YouTube and return the best safe videos, best first."""
    found = client.get(f"{API}/search", params={
        "part": "id", "q": query, "type": "video", "maxResults": 25, "safeSearch": "strict",
        "videoEmbeddable": "true", "videoCategoryId": EDUCATION_CATEGORY, "relevanceLanguage": "en",
        "regionCode": "IN", "key": api_key,
    }).raise_for_status().json().get("items", [])
    ids = [item["id"]["videoId"] for item in found]
    if not ids:
        return []
    videos = client.get(f"{API}/videos", params={
        "part": "snippet,contentDetails,statistics,status", "id": ",".join(ids), "key": api_key,
    }).raise_for_status().json().get("items", [])

    results = []
    for v in videos:
        duration = parse_duration(v["contentDetails"]["duration"])
        title = v["snippet"]["title"]
        if unsafe(v) or not MIN_DURATION_SEC <= duration <= MAX_DURATION_SEC or OTHER_CLASS.search(title):
            continue
        results.append({
            "video_id": v["id"],
            "title": title,
            "channel": v["snippet"]["channelTitle"],
            "duration_sec": duration,
            "score": score(v, duration),
            "purpose": guess_purpose(title),
        })
    return sorted(results, key=lambda r: r["score"], reverse=True)[:limit]
