import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
SEED_DIR = BASE_DIR / "seed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    book TEXT NOT NULL,
    number INTEGER NOT NULL,
    title TEXT NOT NULL,
    ncert_code TEXT UNIQUE NOT NULL,
    syllabus_year TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY,
    chapter_id INTEGER NOT NULL REFERENCES chapters(id),
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    keywords TEXT NOT NULL DEFAULT '',
    videos_fetched_at TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
    title, keywords, chapter, content='', tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('video', 'pdf', 'simulation', 'course', 'article')),
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    video_id TEXT,
    duration_sec INTEGER,
    score REAL NOT NULL DEFAULT 0,
    rating INTEGER CHECK (rating IN (-1, 1)),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS resource_topics (
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    purpose TEXT NOT NULL CHECK (purpose IN ('concept', 'examples', 'application', 'reference')),
    PRIMARY KEY (resource_id, topic_id)
);
CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    login_url TEXT,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS library_entries (
    topic_id INTEGER PRIMARY KEY REFERENCES topics(id),
    first_opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    open_count INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    answer_index INTEGER NOT NULL CHECK (answer_index BETWEEN 0 AND 3),
    explanation TEXT NOT NULL,
    flagged INTEGER NOT NULL DEFAULT 0,
    flag_reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS quizzes (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('topic', 'chapter', 'mistakes')),
    topic_id INTEGER REFERENCES topics(id),
    chapter_id INTEGER REFERENCES chapters(id),
    time_limit_sec INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TEXT,
    score INTEGER,
    total INTEGER NOT NULL,
    confidence INTEGER CHECK (confidence BETWEEN 1 AND 5)
);
CREATE TABLE IF NOT EXISTS quiz_questions (
    quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
    question_id INTEGER NOT NULL REFERENCES questions(id),
    position INTEGER NOT NULL,
    chosen_index INTEGER,
    correct INTEGER,
    PRIMARY KEY (quiz_id, question_id)
);
"""


def db_path() -> str:
    return os.getenv("STUDY_DB_PATH", str(BASE_DIR.parent / "data" / "study.db"))


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    Path(db_path()).parent.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        if not conn.execute("SELECT 1 FROM subjects").fetchone():
            seed_syllabus(conn)
            seed_resources(conn)
            conn.executemany(
                "INSERT INTO platforms (domain, name, login_url, note) VALUES (:domain, :name, :login_url, :note)",
                json.loads((SEED_DIR / "platforms.json").read_text()),
            )


def seed_syllabus(conn: sqlite3.Connection) -> None:
    data = json.loads((SEED_DIR / "syllabus.json").read_text())
    for subject in data["subjects"]:
        subject_id = conn.execute(
            "INSERT INTO subjects (code, name) VALUES (?, ?)", (subject["code"], subject["name"])
        ).lastrowid
        for ch in subject["chapters"]:
            chapter_id = conn.execute(
                "INSERT INTO chapters (subject_id, book, number, title, ncert_code, syllabus_year)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (subject_id, ch["book"], ch["number"], ch["title"], ch["ncert"], data["syllabus_year"]),
            ).lastrowid
            for position, topic in enumerate(ch["topics"], start=1):
                topic_id = conn.execute(
                    "INSERT INTO topics (chapter_id, position, title, keywords) VALUES (?, ?, ?, ?)",
                    (chapter_id, position, topic["title"], topic["keywords"]),
                ).lastrowid
                conn.execute(
                    "INSERT INTO topics_fts (rowid, title, keywords, chapter) VALUES (?, ?, ?, ?)",
                    (topic_id, topic["title"], topic["keywords"], ch["title"]),
                )


def seed_resources(conn: sqlite3.Connection) -> None:
    # Every NCERT chapter PDF is a reference for all topics in that chapter.
    for ch in conn.execute("SELECT id, title, ncert_code, book FROM chapters").fetchall():
        resource_id = add_resource(
            conn, "NCERT", "pdf", f"NCERT {ch['book']} - {ch['title']} (textbook chapter with exercises)",
            f"https://ncert.nic.in/textbook/pdf/{ch['ncert_code']}.pdf",
        )
        topic_ids = [t["id"] for t in conn.execute("SELECT id FROM topics WHERE chapter_id = ?", (ch["id"],))]
        link_topics(conn, resource_id, topic_ids, "reference")

    for r in json.loads((SEED_DIR / "resources.json").read_text()):
        resource_id = add_resource(conn, r["provider"], r["type"], r["title"], r["url"])
        if "subject" in r:
            topic_ids = [t["id"] for t in conn.execute(
                "SELECT t.id FROM topics t JOIN chapters c ON c.id = t.chapter_id"
                " JOIN subjects s ON s.id = c.subject_id WHERE s.code = ?",
                (r["subject"],),
            )]
        else:
            topic_ids = [
                conn.execute(
                    "SELECT t.id FROM topics t JOIN chapters c ON c.id = t.chapter_id"
                    " WHERE c.ncert_code = ? AND t.title = ?",
                    (code, title),
                ).fetchone()["id"]
                for code, title in r["topics"]
            ]
        link_topics(conn, resource_id, topic_ids, "concept")


def add_resource(conn, provider, type_, title, url, video_id=None, duration_sec=None, score=0.0) -> int:
    return conn.execute(
        "INSERT INTO resources (provider, type, title, url, video_id, duration_sec, score)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (provider, type_, title, url, video_id, duration_sec, score),
    ).lastrowid


def link_topics(conn, resource_id: int, topic_ids: list[int], purpose: str) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO resource_topics (resource_id, topic_id, purpose) VALUES (?, ?, ?)",
        [(resource_id, topic_id, purpose) for topic_id in topic_ids],
    )


def platform_for(platforms: list[sqlite3.Row], url: str) -> sqlite3.Row | None:
    """The known site a URL belongs to (exact domain or a subdomain of it), if any."""
    host = (urlparse(url).hostname or "").lower()
    return next((p for p in platforms if host == p["domain"] or host.endswith("." + p["domain"])), None)
