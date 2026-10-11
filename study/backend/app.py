import asyncio
import os
import re
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

import youtube
from auth import new_token, verify_password
from db import add_resource, connect, init_db, link_topics
from search import match_topics

load_dotenv()

INDEX_INTERVAL_SEC = 24 * 3600
LEARN_LIMITS = {"concept": 3, "examples": 2, "application": 2}
VIDEO_ID = re.compile(r"(?:v=|youtu\.be/|embed/|shorts/)([\w-]{11})")


async def index_channels_daily(api_key: str) -> None:
    while True:
        with connect() as conn:
            await asyncio.to_thread(youtube.index_all, conn, api_key)
        await asyncio.sleep(INDEX_INTERVAL_SEC)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    task = None
    if api_key := os.getenv("YOUTUBE_API_KEY"):
        task = asyncio.create_task(index_channels_daily(api_key))
    yield
    if task:
        task.cancel()


app = FastAPI(lifespan=lifespan)


def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]


def current_user(conn: Conn, session: Annotated[str | None, Cookie()] = None) -> sqlite3.Row:
    user = session and conn.execute(
        "SELECT u.id, u.username, u.name, u.role FROM sessions s JOIN users u ON u.id = s.user_id"
        " WHERE s.token = ?",
        (session,),
    ).fetchone()
    if not user:
        raise HTTPException(401, "Not signed in")
    return user


def reviewer(user: Annotated[sqlite3.Row, Depends(current_user)]) -> sqlite3.Row:
    if user["role"] not in ("educator", "parent"):
        raise HTTPException(403, "Reviewers only")
    return user


User = Annotated[sqlite3.Row, Depends(current_user)]
Reviewer = Annotated[sqlite3.Row, Depends(reviewer)]


# --- auth ---------------------------------------------------------------------------------

class Login(BaseModel):
    username: str
    password: str


@app.post("/api/auth/login")
def login(body: Login, conn: Conn, response: Response):
    user = conn.execute("SELECT * FROM users WHERE username = ?", (body.username,)).fetchone()
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Wrong username or password")
    token = new_token()
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user["id"]))
    response.set_cookie(
        "session", token, httponly=True, samesite="lax", secure=os.getenv("COOKIE_SECURE") == "1",
        max_age=30 * 24 * 3600,
    )
    return {"username": user["username"], "name": user["name"], "role": user["role"]}


@app.post("/api/auth/logout")
def logout(conn: Conn, response: Response, session: Annotated[str | None, Cookie()] = None):
    conn.execute("DELETE FROM sessions WHERE token = ?", (session,))
    response.delete_cookie("session")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User):
    return dict(user)


# --- syllabus -----------------------------------------------------------------------------

TOPIC_SELECT = """
SELECT t.id, t.title, c.id AS chapter_id, c.title AS chapter_title, c.book, c.number AS chapter_number,
       s.code AS subject_code, s.name AS subject_name
FROM topics t JOIN chapters c ON c.id = t.chapter_id JOIN subjects s ON s.id = c.subject_id
"""


def topic_summary(conn, topic_ids: list[int]) -> list[dict]:
    by_id = {
        r["id"]: dict(r)
        for r in conn.execute(
            f"{TOPIC_SELECT} WHERE t.id IN ({','.join('?' * len(topic_ids))})", topic_ids
        )
    }
    return [by_id[i] for i in topic_ids if i in by_id]


@app.get("/api/subjects")
def subjects(conn: Conn, _: User):
    return [dict(r) for r in conn.execute(
        "SELECT s.code, s.name, COUNT(c.id) AS chapters FROM subjects s"
        " JOIN chapters c ON c.subject_id = s.id GROUP BY s.id ORDER BY s.id"
    )]


@app.get("/api/subjects/{code}")
def subject(code: str, conn: Conn, _: User):
    s = conn.execute("SELECT id, code, name FROM subjects WHERE code = ?", (code,)).fetchone()
    if not s:
        raise HTTPException(404, "Subject not found")
    chapters = [dict(c) | {"topics": []} for c in conn.execute(
        "SELECT id, book, number, title, syllabus_year FROM chapters WHERE subject_id = ? ORDER BY id", (s["id"],)
    )]
    by_id = {c["id"]: c for c in chapters}
    for t in conn.execute(
        "SELECT t.id, t.title, t.chapter_id FROM topics t JOIN chapters c ON c.id = t.chapter_id"
        " WHERE c.subject_id = ? ORDER BY t.chapter_id, t.position",
        (s["id"],),
    ):
        by_id[t["chapter_id"]]["topics"].append({"id": t["id"], "title": t["title"]})
    return {"code": s["code"], "name": s["name"], "chapters": chapters}


@app.get("/api/topics")
def all_topics(conn: Conn, _: User):
    return [dict(r) for r in conn.execute(f"{TOPIC_SELECT} ORDER BY s.id, c.id, t.position")]


# --- search, topic packs, library ---------------------------------------------------------

@app.get("/api/search")
def search(q: str, conn: Conn, user: User):
    outcome, topic_ids = match_topics(conn, q)
    conn.execute(
        "INSERT INTO searches (user_id, query, outcome, topic_id) VALUES (?, ?, ?, ?)",
        (user["id"], q, outcome, topic_ids[0] if outcome == "match" else None),
    )
    return {"query": q, "outcome": outcome, "topics": topic_summary(conn, topic_ids) if topic_ids else []}


def visible_resources(conn: sqlite3.Connection, topic_id: int) -> list[dict]:
    """The only place that decides what a student may see: verified items only."""
    rows = conn.execute(
        """
        SELECT r.id, r.type, r.title, r.url, r.video_id, r.duration_sec, rt.purpose,
               s.kind AS source_kind, s.name AS source_name, s.tier,
               rv.recommendation, u.name AS reviewer_name
        FROM resources r
        JOIN resource_topics rt ON rt.resource_id = r.id
        JOIN sources s ON s.id = r.source_id
        LEFT JOIN reviews rv ON rv.id = (
            SELECT id FROM reviews WHERE resource_id = r.id AND approved = 1 ORDER BY id DESC LIMIT 1)
        LEFT JOIN users u ON u.id = rv.reviewer_id
        WHERE rt.topic_id = ? AND r.status = 'verified'
        ORDER BY s.tier,
                 (rv.alignment + rv.accuracy + rv.clarity + rv.examples + rv.age_fit) DESC NULLS LAST,
                 r.engagement_score DESC, r.id
        """,
        (topic_id,),
    ).fetchall()
    items = []
    for r in rows:
        item = dict(r)
        item["badge"] = f"Verified by {r['reviewer_name']}" if r["tier"] == 3 else r["source_name"]
        items.append(item)
    return items


def build_pack(items: list[dict]) -> dict:
    learn, counts = [], dict.fromkeys(LEARN_LIMITS, 0)
    for i in items:
        if i["type"] != "video":
            continue
        purpose = i["purpose"] if i["purpose"] in LEARN_LIMITS else "concept"
        if counts[purpose] < LEARN_LIMITS[purpose]:
            counts[purpose] += 1
            learn.append(i)
    return {
        "learn": learn,
        "explore": [i for i in items if i["type"] == "simulation"],
        "read": [i for i in items if i["type"] in ("pdf", "course", "article")],
        "practice": [i for i in items if i["source_kind"] == "ncert" and i["type"] == "pdf"],
    }


@app.get("/api/topics/{topic_id}")
def topic_pack(topic_id: int, conn: Conn, user: User):
    summary = topic_summary(conn, [topic_id])
    if not summary:
        raise HTTPException(404, "Topic not found")
    conn.execute(
        "INSERT INTO library_entries (user_id, topic_id) VALUES (?, ?)"
        " ON CONFLICT DO UPDATE SET open_count = open_count + 1, last_opened_at = CURRENT_TIMESTAMP",
        (user["id"], topic_id),
    )
    return summary[0] | {"tabs": build_pack(visible_resources(conn, topic_id))}


@app.get("/api/library")
def library(conn: Conn, user: User):
    entries = conn.execute(
        "SELECT topic_id, open_count, first_opened_at, last_opened_at FROM library_entries"
        " WHERE user_id = ? ORDER BY last_opened_at DESC, rowid DESC",
        (user["id"],),
    ).fetchall()
    if not entries:
        return []
    summaries = topic_summary(conn, [e["topic_id"] for e in entries])
    return [s | dict(e) for s, e in zip(summaries, entries)]


class Report(BaseModel):
    note: str = ""


@app.post("/api/resources/{resource_id}/report")
def report(resource_id: int, body: Report, conn: Conn, user: User):
    if not conn.execute("SELECT 1 FROM resources WHERE id = ?", (resource_id,)).fetchone():
        raise HTTPException(404, "Resource not found")
    conn.execute(
        "INSERT INTO reports (resource_id, user_id, note) VALUES (?, ?, ?)", (resource_id, user["id"], body.note)
    )
    conn.execute("UPDATE resources SET status = 'hidden' WHERE id = ?", (resource_id,))
    return {"ok": True}


# --- review (educator / parent) -----------------------------------------------------------

QUEUE_PER_TOPIC = 5


@app.get("/api/review/queue")
def review_queue(conn: Conn, _: Reviewer):
    rows = conn.execute(
        """
        SELECT r.id, r.type, r.title, r.url, r.video_id, r.duration_sec, r.engagement_score, r.status,
               rt.topic_id, rt.purpose, s.name AS source_name,
               (SELECT COUNT(*) FROM searches WHERE searches.topic_id = rt.topic_id) AS searches,
               (SELECT group_concat(note, ' | ') FROM reports WHERE reports.resource_id = r.id) AS reports
        FROM resources r
        JOIN resource_topics rt ON rt.resource_id = r.id
        JOIN sources s ON s.id = r.source_id
        WHERE r.status IN ('candidate', 'hidden')
        GROUP BY r.id
        ORDER BY r.status = 'hidden' DESC, searches DESC, r.engagement_score DESC
        """
    ).fetchall()
    per_topic: dict[int, int] = {}
    items = []
    for r in rows:
        if r["status"] == "candidate":
            per_topic[r["topic_id"]] = per_topic.get(r["topic_id"], 0) + 1
            if per_topic[r["topic_id"]] > QUEUE_PER_TOPIC:
                continue
        items.append(dict(r))
    topics = {t["id"]: t for t in topic_summary(conn, list({i["topic_id"] for i in items}))} if items else {}
    return [i | {"topic": topics[i["topic_id"]]} for i in items]


Score = Annotated[int, Field(ge=1, le=5)]


class Review(BaseModel):
    alignment: Score
    accuracy: Score
    clarity: Score
    examples: Score
    age_fit: Score
    approve: bool
    recommendation: str = ""
    topic_id: int | None = None
    purpose: Literal["concept", "examples", "application", "reference"] | None = None


def apply_review(conn, resource_id: int, body: Review, reviewer_id: int) -> str:
    scores = [body.alignment, body.accuracy, body.clarity, body.examples, body.age_fit]
    if body.approve and min(scores) < 3:
        raise HTTPException(400, "Approval needs every rubric score to be 3 or higher")
    if body.topic_id is not None:
        purpose = body.purpose or conn.execute(
            "SELECT purpose FROM resource_topics WHERE resource_id = ?", (resource_id,)
        ).fetchone()["purpose"]
        conn.execute("DELETE FROM resource_topics WHERE resource_id = ?", (resource_id,))
        link_topics(conn, resource_id, [body.topic_id], purpose)
    elif body.purpose:
        conn.execute("UPDATE resource_topics SET purpose = ? WHERE resource_id = ?", (body.purpose, resource_id))
    conn.execute(
        "INSERT INTO reviews (resource_id, reviewer_id, alignment, accuracy, clarity, examples, age_fit,"
        " approved, recommendation) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (resource_id, reviewer_id, *scores, int(body.approve), body.recommendation),
    )
    status = "verified" if body.approve else "rejected"
    conn.execute("UPDATE resources SET status = ? WHERE id = ?", (status, resource_id))
    return status


@app.post("/api/review/resources/{resource_id}")
def review_resource(resource_id: int, body: Review, conn: Conn, user: Reviewer):
    if not conn.execute("SELECT 1 FROM resources WHERE id = ?", (resource_id,)).fetchone():
        raise HTTPException(404, "Resource not found")
    return {"status": apply_review(conn, resource_id, body, user["id"])}


class NewResource(Review):
    title: str = Field(min_length=3)
    url: str = Field(pattern=r"^https://")
    type: Literal["video", "pdf", "simulation", "course", "article"]
    topic_id: int
    purpose: Literal["concept", "examples", "application", "reference"]


@app.post("/api/review/resources")
def add_reviewed_resource(body: NewResource, conn: Conn, user: Reviewer):
    if conn.execute("SELECT 1 FROM resources WHERE url = ?", (body.url,)).fetchone():
        raise HTTPException(409, "This link is already in the library")
    source = conn.execute("SELECT id FROM sources WHERE kind = 'educator'").fetchone()
    source_id = source["id"] if source else conn.execute(
        "INSERT INTO sources (kind, name, tier) VALUES ('educator', 'Educator recommendation', 3)"
    ).lastrowid
    video_id = m.group(1) if body.type == "video" and (m := VIDEO_ID.search(body.url)) else None
    if body.type == "video" and not video_id:
        raise HTTPException(400, "Videos must be YouTube links")
    resource_id = add_resource(conn, source_id, body.type, body.title, body.url, "candidate", video_id=video_id)
    link_topics(conn, resource_id, [body.topic_id], body.purpose)
    return {"id": resource_id, "status": apply_review(conn, resource_id, body, user["id"])}


@app.get("/api/review/sources")
def list_sources(conn: Conn, _: Reviewer):
    return [dict(r) for r in conn.execute(
        "SELECT s.id, s.kind, s.name, s.external_id, s.tier, s.created_at, u.name AS approved_by,"
        " (SELECT COUNT(*) FROM resources WHERE source_id = s.id) AS resources"
        " FROM sources s LEFT JOIN users u ON u.id = s.approved_by ORDER BY s.tier, s.id"
    )]


class NewChannel(BaseModel):
    handle: str = Field(min_length=2)
    tier: Literal[1, 3] = 3


def youtube_key() -> str:
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        raise HTTPException(400, "YOUTUBE_API_KEY is not configured on the server")
    return key


@app.post("/api/review/sources")
def add_channel(body: NewChannel, conn: Conn, user: Reviewer):
    with httpx.Client(timeout=30) as client:
        try:
            channel = youtube.resolve_channel(client, youtube_key(), body.handle.strip())
        except ValueError as e:
            raise HTTPException(404, str(e))
    if conn.execute(
        "SELECT 1 FROM sources WHERE kind = 'youtube_channel' AND external_id = ?", (channel["id"],)
    ).fetchone():
        raise HTTPException(409, "Channel is already allow-listed")
    source_id = conn.execute(
        "INSERT INTO sources (kind, name, external_id, tier, approved_by) VALUES ('youtube_channel', ?, ?, ?, ?)",
        (channel["title"], channel["id"], body.tier, user["id"]),
    ).lastrowid
    return {"id": source_id, "name": channel["title"]}


@app.post("/api/review/sources/{source_id}/index")
def index_source(source_id: int, conn: Conn, _: Reviewer):
    source = conn.execute(
        "SELECT * FROM sources WHERE id = ? AND kind = 'youtube_channel'", (source_id,)
    ).fetchone()
    if not source:
        raise HTTPException(404, "YouTube channel not found")
    with httpx.Client(timeout=30) as client:
        return {"added": youtube.index_channel(conn, client, youtube_key(), source)}


@app.get("/api/review/searches")
def recent_searches(conn: Conn, _: Reviewer):
    return [dict(r) for r in conn.execute(
        "SELECT se.id, se.query, se.outcome, se.created_at, u.name AS user_name, t.title AS topic_title"
        " FROM searches se JOIN users u ON u.id = se.user_id LEFT JOIN topics t ON t.id = se.topic_id"
        " ORDER BY se.id DESC LIMIT 100"
    )]
