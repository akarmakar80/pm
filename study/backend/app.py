import json
import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

import quiz
import youtube
from db import add_resource, connect, init_db, link_topics, platform_for
from safety import is_blocked
from search import match_topics

load_dotenv()

LEARN_LIMITS = {"concept": 3, "examples": 2, "application": 2}

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


Conn = Annotated[sqlite3.Connection, Depends(get_conn)]

TOPIC_SELECT = """
SELECT t.id, t.title, c.id AS chapter_id, c.title AS chapter_title, c.book, c.number AS chapter_number,
       s.code AS subject_code, s.name AS subject_name
FROM topics t JOIN chapters c ON c.id = t.chapter_id JOIN subjects s ON s.id = c.subject_id
"""


def topic_summary(conn, topic_ids: list[int]) -> list[dict]:
    by_id = {
        r["id"]: dict(r)
        for r in conn.execute(f"{TOPIC_SELECT} WHERE t.id IN ({','.join('?' * len(topic_ids))})", topic_ids)
    }
    return [by_id[i] for i in topic_ids if i in by_id]


# --- syllabus and search ------------------------------------------------------------------

@app.get("/api/subjects")
def subjects(conn: Conn):
    return [dict(r) for r in conn.execute(
        "SELECT s.code, s.name, COUNT(c.id) AS chapters FROM subjects s"
        " JOIN chapters c ON c.subject_id = s.id GROUP BY s.id ORDER BY s.id"
    )]


@app.get("/api/subjects/{code}")
def subject(code: str, conn: Conn):
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


@app.get("/api/search")
def search(q: str, conn: Conn):
    outcome, topic_ids = ("blocked", []) if is_blocked(q) else match_topics(conn, q)
    return {"query": q, "outcome": outcome, "topics": topic_summary(conn, topic_ids) if topic_ids else []}


# --- topic packs ----------------------------------------------------------------------------

def fetch_videos(conn, topic: dict) -> None:
    """Search YouTube for the topic once and save the results."""
    key = os.getenv("YOUTUBE_API_KEY")
    if not key:
        return
    query = f"{topic['title']} class 10 {topic['subject_name']} CBSE NCERT"
    with httpx.Client(timeout=30) as client:
        videos = youtube.find_videos(client, key, query)
    for v in videos:
        url = f"https://www.youtube.com/watch?v={v['video_id']}"
        existing = conn.execute("SELECT id FROM resources WHERE url = ?", (url,)).fetchone()
        resource_id = existing["id"] if existing else add_resource(
            conn, v["channel"], "video", v["title"], url, v["video_id"], v["duration_sec"], v["score"]
        )
        link_topics(conn, resource_id, [topic["id"]], v["purpose"])
    conn.execute("UPDATE topics SET videos_fetched_at = CURRENT_TIMESTAMP WHERE id = ?", (topic["id"],))


def topic_resources(conn, topic_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT r.id, r.provider, r.type, r.title, r.url, r.video_id, r.duration_sec, r.rating, rt.purpose
        FROM resources r JOIN resource_topics rt ON rt.resource_id = r.id
        WHERE rt.topic_id = ? AND r.rating IS NOT -1
        ORDER BY r.rating = 1 DESC, r.score DESC, r.id""",
        (topic_id,),
    ).fetchall()
    platforms = conn.execute("SELECT name, domain, login_url, note FROM platforms").fetchall()
    items = []
    for r in rows:
        platform = platform_for(platforms, r["url"])
        items.append(dict(r) | {"platform": dict(platform) if platform else None})
    return items


def build_pack(items: list[dict]) -> dict:
    learn, counts = [], dict.fromkeys(LEARN_LIMITS, 0)
    for i in items:
        if i["type"] == "video" and counts[i["purpose"]] < LEARN_LIMITS[i["purpose"]]:
            counts[i["purpose"]] += 1
            learn.append(i)
    return {
        "learn": learn,
        "explore": [i for i in items if i["type"] == "simulation"],
        "read": [i for i in items if i["type"] in ("pdf", "course", "article")],
        "practice": [i for i in items if i["provider"] == "NCERT"],
    }


@app.get("/api/topics/{topic_id}")
def topic_pack(topic_id: int, conn: Conn):
    summary = topic_summary(conn, [topic_id])
    if not summary:
        raise HTTPException(404, "Topic not found")
    topic = summary[0]
    if not conn.execute("SELECT videos_fetched_at FROM topics WHERE id = ?", (topic_id,)).fetchone()[0]:
        try:
            fetch_videos(conn, topic)
        except httpx.HTTPError:
            pass  # e.g. daily YouTube quota used up; the next visit tries again
    conn.execute(
        "INSERT INTO library_entries (topic_id) VALUES (?)"
        " ON CONFLICT DO UPDATE SET open_count = open_count + 1, last_opened_at = CURRENT_TIMESTAMP",
        (topic_id,),
    )
    return topic | {
        "tabs": build_pack(topic_resources(conn, topic_id)),
        "videos_enabled": bool(os.getenv("YOUTUBE_API_KEY")),
    }


@app.post("/api/topics/{topic_id}/videos")
def refresh_videos(topic_id: int, conn: Conn):
    summary = topic_summary(conn, [topic_id])
    if not summary:
        raise HTTPException(404, "Topic not found")
    try:
        fetch_videos(conn, summary[0])
    except httpx.HTTPError:
        raise HTTPException(502, "YouTube is not responding or the daily limit is used up. Try again later.")
    return {"ok": True}


@app.get("/api/library")
def library(conn: Conn):
    entries = conn.execute(
        "SELECT topic_id, open_count, last_opened_at FROM library_entries ORDER BY last_opened_at DESC, rowid DESC"
    ).fetchall()
    summaries = {s["id"]: s for s in topic_summary(conn, [e["topic_id"] for e in entries])} if entries else {}
    return [summaries[e["topic_id"]] | dict(e) for e in entries]


@app.get("/api/platforms")
def platforms(conn: Conn):
    return [dict(r) for r in conn.execute("SELECT domain, name, login_url, note FROM platforms ORDER BY name")]


# --- feedback -------------------------------------------------------------------------------

class Rating(BaseModel):
    helpful: bool


@app.post("/api/resources/{resource_id}/rating")
def rate_resource(resource_id: int, body: Rating, conn: Conn):
    """Helpful items move to the top; not-helpful items are hidden."""
    if not conn.execute("UPDATE resources SET rating = ? WHERE id = ?", (1 if body.helpful else -1, resource_id)).rowcount:
        raise HTTPException(404, "Resource not found")
    return {"ok": True}


class Flag(BaseModel):
    reason: str = ""


@app.post("/api/questions/{question_id}/flag")
def flag_question(question_id: int, body: Flag, conn: Conn):
    """A reported question is never used again."""
    if not conn.execute(
        "UPDATE questions SET flagged = 1, flag_reason = ? WHERE id = ?", (body.reason, question_id)
    ).rowcount:
        raise HTTPException(404, "Question not found")
    return {"ok": True}


# --- quizzes --------------------------------------------------------------------------------

class NewQuiz(BaseModel):
    kind: Literal["topic", "chapter", "mistakes"]
    topic_id: int | None = None
    chapter_id: int | None = None


@app.post("/api/quizzes")
def create_quiz(body: NewQuiz, conn: Conn):
    if (body.kind == "topic" and body.topic_id is None) or (body.kind == "chapter" and body.chapter_id is None):
        raise HTTPException(400, f"A {body.kind} quiz needs a {body.kind}")
    try:
        quiz_id = quiz.create(conn, body.kind, body.topic_id, body.chapter_id)
    except quiz.GenerationError as e:
        raise HTTPException(400, str(e))
    except httpx.HTTPError:
        raise HTTPException(502, "The question service is not responding. Please try again in a minute.")
    return {"id": quiz_id}


def quiz_title(conn, z) -> str:
    if z["kind"] == "topic":
        return conn.execute("SELECT title FROM topics WHERE id = ?", (z["topic_id"],)).fetchone()[0]
    if z["kind"] == "chapter":
        return "Chapter test: " + conn.execute("SELECT title FROM chapters WHERE id = ?", (z["chapter_id"],)).fetchone()[0]
    return "My mistakes"


@app.get("/api/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, conn: Conn):
    z = conn.execute("SELECT * FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not z:
        raise HTTPException(404, "Quiz not found")
    submitted = z["submitted_at"] is not None
    questions = []
    for r in conn.execute(
        "SELECT q.id, q.topic_id, q.question, q.options_json, q.answer_index, q.explanation, q.flagged,"
        " qq.chosen_index, qq.correct FROM quiz_questions qq JOIN questions q ON q.id = qq.question_id"
        " WHERE qq.quiz_id = ? ORDER BY qq.position",
        (quiz_id,),
    ):
        item = {"id": r["id"], "topic_id": r["topic_id"], "question": r["question"],
                "options": json.loads(r["options_json"])}
        if submitted:  # answers are only revealed after submission
            item |= {"answer_index": r["answer_index"], "explanation": r["explanation"],
                     "chosen_index": r["chosen_index"], "correct": bool(r["correct"]), "flagged": bool(r["flagged"])}
        questions.append(item)
    return dict(z) | {"title": quiz_title(conn, z), "questions": questions}


class Answers(BaseModel):
    answers: dict[int, int]


@app.post("/api/quizzes/{quiz_id}/submit")
def submit_quiz(quiz_id: int, body: Answers, conn: Conn):
    z = conn.execute("SELECT submitted_at FROM quizzes WHERE id = ?", (quiz_id,)).fetchone()
    if not z:
        raise HTTPException(404, "Quiz not found")
    if z["submitted_at"]:
        raise HTTPException(409, "This quiz was already submitted")
    quiz.submit(conn, quiz_id, body.answers)
    return get_quiz(quiz_id, conn)


class Confidence(BaseModel):
    value: Annotated[int, Field(ge=1, le=5)]


@app.post("/api/quizzes/{quiz_id}/confidence")
def set_confidence(quiz_id: int, body: Confidence, conn: Conn):
    if not conn.execute("UPDATE quizzes SET confidence = ? WHERE id = ?", (body.value, quiz_id)).rowcount:
        raise HTTPException(404, "Quiz not found")
    return {"ok": True}


# --- progress -------------------------------------------------------------------------------

WEAK_ACCURACY = 0.6


@app.get("/api/progress")
def progress(conn: Conn):
    topic_rows = conn.execute(
        """SELECT q.topic_id, COUNT(*) AS answered, SUM(qq.correct) AS correct, MAX(z.submitted_at) AS last_practiced
        FROM quiz_questions qq JOIN questions q ON q.id = qq.question_id
        JOIN quizzes z ON z.id = qq.quiz_id AND z.submitted_at IS NOT NULL
        GROUP BY q.topic_id ORDER BY last_practiced DESC"""
    ).fetchall()
    summaries = {s["id"]: s for s in topic_summary(conn, [r["topic_id"] for r in topic_rows])} if topic_rows else {}
    topics = [
        summaries[r["topic_id"]] | {
            "answered": r["answered"], "correct": r["correct"], "accuracy": round(r["correct"] / r["answered"], 2),
            "last_practiced": r["last_practiced"],
        }
        for r in topic_rows
    ]
    quizzes = [
        dict(z) | {"title": quiz_title(conn, z)}
        for z in conn.execute(
            "SELECT id, kind, topic_id, chapter_id, submitted_at, score, total, confidence FROM quizzes"
            " WHERE submitted_at IS NOT NULL ORDER BY id DESC LIMIT 20"
        )
    ]
    return {
        "topics": topics,
        "weak": [t for t in topics if t["answered"] >= 3 and t["accuracy"] < WEAK_ACCURACY],
        "quizzes": quizzes,
        "mistakes": len(quiz.mistakes(conn)),
    }
