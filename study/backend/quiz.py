"""Multiple-choice questions written by an LLM per syllabus topic, cached and reused across quizzes."""

import json
import os
import re
import sqlite3

import httpx

from safety import is_blocked

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TOPIC_QUIZ_SIZE = 5
CHAPTER_TEST_SIZE = 10
MISTAKES_QUIZ_SIZE = 10
SECONDS_PER_QUESTION = 60

PROMPT = """You write practice questions for a CBSE Class 10 student in India.
Subject: {subject}. Chapter: {chapter}.
Write {count} multiple-choice questions spread across these topics:
{topics}

Rules:
- Follow the current NCERT textbook and CBSE Class 10 level. Mix recall, understanding, application
  and assertion-reason style questions, like CBSE board papers.
- Exactly 4 options per question and exactly one correct option. Options must be distinct.
- Double-check every fact, number and calculation before answering.
- The explanation teaches why the answer is right in 1-3 sentences.

Reply with JSON only, no other text:
{{"questions": [{{"topic": <topic number>, "question": "...", "options": ["...", "...", "...", "..."],
"answer": <index 0-3 of the correct option>, "explanation": "..."}}]}}"""


class GenerationError(Exception):
    pass


def call_llm(prompt: str) -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise GenerationError("Quizzes need OPENROUTER_API_KEY to be set in .env")
    resp = httpx.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free"),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_questions(text: str, topic_ids: list[int]) -> list[dict]:
    """Extract valid questions from the LLM reply; invalid ones are dropped."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return []
    try:
        items = json.loads(match.group(0)).get("questions", [])
    except json.JSONDecodeError:
        return []
    valid = []
    for q in items:
        options = q.get("options")
        answer = q.get("answer")
        topic = q.get("topic")
        if not (
            isinstance(q.get("question"), str) and q["question"].strip()
            and isinstance(options, list) and len(options) == 4
            and all(isinstance(o, str) and o.strip() for o in options)
            and len({o.strip().lower() for o in options}) == 4
            and isinstance(answer, int) and 0 <= answer <= 3
            and isinstance(q.get("explanation"), str)
            and isinstance(topic, int) and 1 <= topic <= len(topic_ids)
            and not is_blocked(" ".join([q["question"], *options, q["explanation"]]))
        ):
            continue
        valid.append({
            "topic_id": topic_ids[topic - 1],
            "question": q["question"].strip(),
            "options": [o.strip() for o in options],
            "answer_index": answer,
            "explanation": q["explanation"].strip(),
        })
    return valid


def generate(conn: sqlite3.Connection, topic_ids: list[int], count: int) -> int:
    topics = conn.execute(
        f"SELECT t.id, t.title, t.keywords, c.title AS chapter, s.name AS subject FROM topics t"
        f" JOIN chapters c ON c.id = t.chapter_id JOIN subjects s ON s.id = c.subject_id"
        f" WHERE t.id IN ({','.join('?' * len(topic_ids))}) ORDER BY t.position",
        topic_ids,
    ).fetchall()
    prompt = PROMPT.format(
        subject=topics[0]["subject"],
        chapter=topics[0]["chapter"],
        count=count,
        topics="\n".join(f"{i}. {t['title']} ({t['keywords']})" for i, t in enumerate(topics, start=1)),
    )
    questions = parse_questions(call_llm(prompt), [t["id"] for t in topics])
    if not questions:
        raise GenerationError("Could not create questions right now. Please try again.")
    conn.executemany(
        "INSERT INTO questions (topic_id, question, options_json, answer_index, explanation)"
        " VALUES (:topic_id, :question, :options, :answer_index, :explanation)",
        [q | {"options": json.dumps(q["options"])} for q in questions],
    )
    return len(questions)


def available(conn, topic_ids: list[int]) -> int:
    return conn.execute(
        f"SELECT COUNT(*) FROM questions WHERE flagged = 0 AND topic_id IN ({','.join('?' * len(topic_ids))})",
        topic_ids,
    ).fetchone()[0]


def pick(conn, topic_ids: list[int], count: int) -> list[int]:
    """Prefer questions never answered correctly, then random."""
    rows = conn.execute(
        f"""SELECT q.id FROM questions q
        WHERE q.flagged = 0 AND q.topic_id IN ({','.join('?' * len(topic_ids))})
        ORDER BY EXISTS (SELECT 1 FROM quiz_questions qq WHERE qq.question_id = q.id AND qq.correct = 1),
                 random()
        LIMIT ?""",
        [*topic_ids, count],
    ).fetchall()
    return [r["id"] for r in rows]


def mistakes(conn) -> list[int]:
    """Questions whose most recent answer was wrong."""
    rows = conn.execute(
        """SELECT qq.question_id FROM quiz_questions qq
        JOIN questions q ON q.id = qq.question_id AND q.flagged = 0
        JOIN quizzes z ON z.id = qq.quiz_id AND z.submitted_at IS NOT NULL
        WHERE qq.correct IS NOT NULL AND z.id = (
            SELECT MAX(z2.id) FROM quiz_questions qq2 JOIN quizzes z2 ON z2.id = qq2.quiz_id
            WHERE qq2.question_id = qq.question_id AND z2.submitted_at IS NOT NULL)
          AND qq.correct = 0
        ORDER BY z.id DESC LIMIT ?""",
        (MISTAKES_QUIZ_SIZE,),
    ).fetchall()
    return [r["question_id"] for r in rows]


def create(conn, kind: str, topic_id: int | None = None, chapter_id: int | None = None) -> int:
    if kind == "mistakes":
        question_ids = mistakes(conn)
        if not question_ids:
            raise GenerationError("No mistakes to practise. Well done!")
        time_limit = None
    else:
        topic_ids = [topic_id] if kind == "topic" else [
            r["id"] for r in conn.execute("SELECT id FROM topics WHERE chapter_id = ? ORDER BY position", (chapter_id,))
        ]
        size = TOPIC_QUIZ_SIZE if kind == "topic" else CHAPTER_TEST_SIZE
        if available(conn, topic_ids) < size:
            generate(conn, topic_ids, size + 3)
        question_ids = pick(conn, topic_ids, size)
        time_limit = len(question_ids) * SECONDS_PER_QUESTION if kind == "chapter" else None

    quiz_id = conn.execute(
        "INSERT INTO quizzes (kind, topic_id, chapter_id, time_limit_sec, total) VALUES (?, ?, ?, ?, ?)",
        (kind, topic_id, chapter_id, time_limit, len(question_ids)),
    ).lastrowid
    conn.executemany(
        "INSERT INTO quiz_questions (quiz_id, question_id, position) VALUES (?, ?, ?)",
        [(quiz_id, qid, i) for i, qid in enumerate(question_ids)],
    )
    return quiz_id


def submit(conn, quiz_id: int, answers: dict[int, int]) -> None:
    rows = conn.execute(
        "SELECT qq.question_id, q.answer_index FROM quiz_questions qq JOIN questions q ON q.id = qq.question_id"
        " WHERE qq.quiz_id = ?",
        (quiz_id,),
    ).fetchall()
    for r in rows:
        chosen = answers.get(r["question_id"])
        conn.execute(
            "UPDATE quiz_questions SET chosen_index = ?, correct = ? WHERE quiz_id = ? AND question_id = ?",
            (chosen, int(chosen == r["answer_index"]), quiz_id, r["question_id"]),
        )
    conn.execute(
        "UPDATE quizzes SET submitted_at = CURRENT_TIMESTAMP,"
        " score = (SELECT SUM(correct) FROM quiz_questions WHERE quiz_id = ?) WHERE id = ?",
        (quiz_id, quiz_id),
    )
