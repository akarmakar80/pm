import json
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

from auth import hash_password

BASE_DIR = Path(__file__).resolve().parent
SEED_DIR = BASE_DIR / "seed"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'educator', 'parent')),
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
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
    keywords TEXT NOT NULL DEFAULT ''
);
CREATE VIRTUAL TABLE IF NOT EXISTS topics_fts USING fts5(
    title, keywords, chapter, content='', tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,
    name TEXT NOT NULL,
    external_id TEXT,
    tier INTEGER NOT NULL CHECK (tier BETWEEN 1 AND 3),
    approved_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (kind, external_id)
);
CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    type TEXT NOT NULL CHECK (type IN ('video', 'pdf', 'simulation', 'course', 'article')),
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    video_id TEXT,
    duration_sec INTEGER,
    published_at TEXT,
    engagement_score REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL CHECK (status IN ('candidate', 'verified', 'rejected', 'hidden')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS resource_topics (
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    purpose TEXT NOT NULL CHECK (purpose IN ('concept', 'examples', 'application', 'reference')),
    PRIMARY KEY (resource_id, topic_id)
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    reviewer_id INTEGER NOT NULL REFERENCES users(id),
    alignment INTEGER NOT NULL,
    accuracy INTEGER NOT NULL,
    clarity INTEGER NOT NULL,
    examples INTEGER NOT NULL,
    age_fit INTEGER NOT NULL,
    approved INTEGER NOT NULL,
    recommendation TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY,
    resource_id INTEGER NOT NULL REFERENCES resources(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS searches (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    query TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('match', 'choose', 'out_of_syllabus', 'blocked')),
    topic_id INTEGER REFERENCES topics(id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS platforms (
    id INTEGER PRIMARY KEY,
    domain TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    login_url TEXT,
    note TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS library_entries (
    user_id INTEGER NOT NULL REFERENCES users(id),
    topic_id INTEGER NOT NULL REFERENCES topics(id),
    first_opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    open_count INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (user_id, topic_id)
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
        if not conn.execute("SELECT 1 FROM users").fetchone():
            seed_users(conn)
        if not conn.execute("SELECT 1 FROM subjects").fetchone():
            seed_syllabus(conn)
            seed_resources(conn)
        if not conn.execute("SELECT 1 FROM platforms").fetchone():
            conn.executemany(
                "INSERT INTO platforms (domain, name, login_url, note) VALUES (:domain, :name, :login_url, :note)",
                json.loads((SEED_DIR / "platforms.json").read_text()),
            )


def seed_users(conn: sqlite3.Connection) -> None:
    for username, name, role in [
        ("student", "Student", "student"),
        ("parent", "Parent", "parent"),
        ("educator", "Educator", "educator"),
    ]:
        password = os.getenv(f"{role.upper()}_PASSWORD", username)
        conn.execute(
            "INSERT INTO users (username, name, role, password_hash) VALUES (?, ?, ?, ?)",
            (username, name, role, hash_password(password)),
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
    data = json.loads((SEED_DIR / "resources.json").read_text())
    source_ids = {}
    for s in data["sources"]:
        source_ids[s["kind"]] = conn.execute(
            "INSERT INTO sources (kind, name, tier) VALUES (?, ?, ?)", (s["kind"], s["name"], s["tier"])
        ).lastrowid

    # Every NCERT chapter PDF is a reference for all topics in that chapter.
    for ch in conn.execute("SELECT id, title, ncert_code, book FROM chapters").fetchall():
        resource_id = add_resource(
            conn,
            source_ids["ncert"],
            "pdf",
            f"NCERT {ch['book']} - {ch['title']} (textbook chapter with exercises)",
            f"https://ncert.nic.in/textbook/pdf/{ch['ncert_code']}.pdf",
            "verified",
        )
        link_topics(conn, resource_id, [t["id"] for t in conn.execute(
            "SELECT id FROM topics WHERE chapter_id = ?", (ch["id"],)
        )], "reference")

    for r in data["resources"]:
        resource_id = add_resource(conn, source_ids[r["source"]], r["type"], r["title"], r["url"], "verified")
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


def add_resource(conn, source_id, type_, title, url, status, video_id=None, duration_sec=None,
                 published_at=None, engagement_score=0.0) -> int:
    return conn.execute(
        "INSERT INTO resources (source_id, type, title, url, video_id, duration_sec, published_at,"
        " engagement_score, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (source_id, type_, title, url, video_id, duration_sec, published_at, engagement_score, status),
    ).lastrowid


def link_topics(conn, resource_id: int, topic_ids: list[int], purpose: str) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO resource_topics (resource_id, topic_id, purpose) VALUES (?, ?, ?)",
        [(resource_id, topic_id, purpose) for topic_id in topic_ids],
    )


def platform_for(platforms: list[sqlite3.Row], url: str) -> sqlite3.Row | None:
    """The allow-listed site a URL belongs to (exact domain or a subdomain of it), if any."""
    host = (urlparse(url).hostname or "").lower()
    return next((p for p in platforms if host == p["domain"] or host.endswith("." + p["domain"])), None)
