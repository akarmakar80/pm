"""Index videos from allow-listed YouTube channels into the local database.

Only channels in the `sources` table are read. Videos from tier 1-2 channels are verified
immediately; videos from tier 3 channels become candidates for educator review.
"""

import math
import re
import sqlite3
from datetime import UTC, datetime

import httpx

from db import add_resource, link_topics
from search import match_topics

API = "https://www.googleapis.com/youtube/v3"
OTHER_CLASS = re.compile(r"\b(class|std|grade)\s*-?\s*(6|7|8|9|11|12)(th)?\b", re.IGNORECASE)
MIN_DURATION_SEC = 120


def resolve_channel(client: httpx.Client, api_key: str, handle_or_id: str) -> dict:
    params = {"part": "snippet,contentDetails", "key": api_key}
    if handle_or_id.startswith("UC"):
        params["id"] = handle_or_id
    else:
        params["forHandle"] = handle_or_id if handle_or_id.startswith("@") else f"@{handle_or_id}"
    items = client.get(f"{API}/channels", params=params).raise_for_status().json().get("items", [])
    if not items:
        raise ValueError(f"YouTube channel not found: {handle_or_id}")
    item = items[0]
    return {
        "id": item["id"],
        "title": item["snippet"]["title"],
        "uploads": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def parse_duration(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    days, hours, minutes, seconds = (int(g or 0) for g in m.groups())
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def guess_purpose(title: str) -> str:
    t = title.lower()
    if any(w in t for w in ("real life", "daily life", "application", "in everyday", "practical")):
        return "application"
    if any(w in t for w in ("example", "solved", "solution", "exercise", "questions", "numericals", "pyq")):
        return "examples"
    return "concept"


def engagement_score(views: int, likes: int, comments: int, duration_sec: int, published_at: str) -> float:
    engagement = (likes + 2 * comments) / max(views, 1)
    duration_fit = 1.0 if 360 <= duration_sec <= 1500 else 0.5
    age_years = (datetime.now(UTC) - datetime.fromisoformat(published_at)).days / 365
    recency = max(0.0, 1 - age_years / 6)
    return round(
        0.40 * min(math.log10(views + 1) / 7, 1)
        + 0.30 * min(engagement * 20, 1)
        + 0.15 * duration_fit
        + 0.15 * recency,
        4,
    )


def index_channel(conn: sqlite3.Connection, client: httpx.Client, api_key: str, source: sqlite3.Row,
                  max_pages: int = 20) -> int:
    """Read the channel's uploads and store new on-syllabus videos. Returns the number added."""
    channel = resolve_channel(client, api_key, source["external_id"])
    status = "verified" if source["tier"] <= 2 else "candidate"
    added = 0
    page_token = None
    for _ in range(max_pages):
        params = {"part": "contentDetails", "playlistId": channel["uploads"], "maxResults": 50, "key": api_key}
        if page_token:
            params["pageToken"] = page_token
        page = client.get(f"{API}/playlistItems", params=params).raise_for_status().json()
        ids = [item["contentDetails"]["videoId"] for item in page.get("items", [])]
        if ids:
            added += store_videos(conn, client, api_key, source["id"], ids, status)
        page_token = page.get("nextPageToken")
        if not page_token:
            break
    return added


def store_videos(conn, client, api_key, source_id, video_ids, status) -> int:
    videos = client.get(
        f"{API}/videos",
        params={"part": "snippet,contentDetails,statistics,status", "id": ",".join(video_ids), "key": api_key},
    ).raise_for_status().json().get("items", [])
    added = 0
    for v in videos:
        title = v["snippet"]["title"]
        duration = parse_duration(v["contentDetails"]["duration"])
        url = f"https://www.youtube.com/watch?v={v['id']}"
        if (
            not v["status"].get("embeddable", False)
            or duration < MIN_DURATION_SEC
            or OTHER_CLASS.search(title)
            or conn.execute("SELECT 1 FROM resources WHERE url = ?", (url,)).fetchone()
        ):
            continue
        outcome, topic_ids = match_topics(conn, title, limit=1, include_chapter=False)
        if outcome == "out_of_syllabus":
            continue
        stats = v.get("statistics", {})
        published_at = v["snippet"]["publishedAt"].replace("Z", "+00:00")
        resource_id = add_resource(
            conn, source_id, "video", title, url, status,
            video_id=v["id"],
            duration_sec=duration,
            published_at=published_at,
            engagement_score=engagement_score(
                int(stats.get("viewCount", 0)), int(stats.get("likeCount", 0)),
                int(stats.get("commentCount", 0)), duration, published_at,
            ),
        )
        link_topics(conn, resource_id, topic_ids, guess_purpose(title))
        added += 1
    return added


def index_all(conn: sqlite3.Connection, api_key: str) -> int:
    sources = conn.execute("SELECT * FROM sources WHERE kind = 'youtube_channel'").fetchall()
    with httpx.Client(timeout=30) as client:
        return sum(index_channel(conn, client, api_key, s) for s in sources)
