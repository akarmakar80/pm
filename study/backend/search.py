import re
import sqlite3

STOPWORDS = {
    "a", "an", "and", "are", "about", "class", "cbse", "chapter", "do", "does", "explain", "for", "how",
    "in", "is", "it", "learn", "me", "ncert", "of", "on", "or", "study", "teach", "the", "to", "what",
    "why", "with", "10", "10th", "x", "full", "one", "shot", "explained", "part", "lecture", "hindi",
    "english", "board", "exam", "science", "maths", "mathematics", "lesson", "notes", "our", "from",
    "your", "my", "this", "that", "all", "best", "easy", "trick", "tricks", "video", "complete",
}

# A single match is chosen when its score is clearly better than the runner-up.
# bm25 scores are negative: lower is better.
CLEAR_WINNER_RATIO = 1.5


def tokens(query: str) -> list[str]:
    return [t for t in re.findall(r"\w+", query.lower()) if len(t) > 1 and t not in STOPWORDS]


def match_topics(conn: sqlite3.Connection, query: str, limit: int = 5,
                 include_chapter: bool = True) -> tuple[str, list[int]]:
    """Map a free-text query onto syllabus topics.

    Returns ("match", [topic_id]), ("choose", [topic_ids...]) or ("out_of_syllabus", []).
    include_chapter=False matches topic titles and keywords only, for stricter tagging of video titles.
    """
    terms = tokens(query)
    if not terms:
        return "out_of_syllabus", []
    fts_query = " OR ".join(f'"{t}"*' for t in terms)
    if not include_chapter:
        fts_query = f"{{title keywords}}: ({fts_query})"
    rows = conn.execute(
        "SELECT rowid AS id, bm25(topics_fts, 10.0, 3.0, 2.0) AS score FROM topics_fts"
        " WHERE topics_fts MATCH ? ORDER BY score LIMIT ?",
        (fts_query, limit),
    ).fetchall()
    if not rows:
        return "out_of_syllabus", []
    exact = conn.execute(
        "SELECT id FROM topics WHERE lower(title) = ?", (query.strip().lower(),)
    ).fetchone()
    if exact:
        return "match", [exact["id"]]
    if len(rows) == 1 or rows[0]["score"] <= CLEAR_WINNER_RATIO * rows[1]["score"]:
        return "match", [rows[0]["id"]]
    return "choose", [r["id"] for r in rows]
