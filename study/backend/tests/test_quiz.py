import json

import pytest

import quiz
from conftest import topic_id


def llm_reply(topics: int, count: int) -> str:
    return json.dumps({"questions": [
        {"topic": i % topics + 1, "question": f"Question {i}?", "options": [f"A{i}", f"B{i}", f"C{i}", f"D{i}"],
         "answer": 1, "explanation": f"Because B{i}."}
        for i in range(count)
    ]})


@pytest.fixture
def llm(monkeypatch):
    prompts = []
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")

    def fake(prompt):
        prompts.append(prompt)
        topics = prompt.count("\n", prompt.index("these topics:"), prompt.index("Rules:")) - 2
        count = int(prompt.split("Write ")[1].split(" ")[0])
        return "Here you go:\n" + llm_reply(topics, count)

    monkeypatch.setattr(quiz, "call_llm", fake)
    return prompts


def test_parse_questions_drops_invalid():
    good = {"topic": 1, "question": "Q?", "options": ["a", "b", "c", "d"], "answer": 0, "explanation": "e"}
    text = json.dumps({"questions": [
        good,
        good | {"options": ["a", "b", "c"]},
        good | {"options": ["a", "a", "c", "d"]},
        good | {"answer": 4},
        good | {"topic": 2},
        good | {"question": "porn?"},
    ]})
    assert len(quiz.parse_questions(text, [10])) == 1
    assert quiz.parse_questions("not json", [10]) == []


def test_quiz_needs_api_key(client):
    tid = topic_id(client, "ohms law")
    r = client.post("/api/quizzes", json={"kind": "topic", "topic_id": tid})
    assert r.status_code == 400 and "OPENROUTER_API_KEY" in r.json()["detail"]


def test_topic_quiz_flow(client, llm):
    tid = topic_id(client, "ohms law")
    quiz_id = client.post("/api/quizzes", json={"kind": "topic", "topic_id": tid}).json()["id"]
    z = client.get(f"/api/quizzes/{quiz_id}").json()
    assert len(z["questions"]) == 5 and "answer_index" not in z["questions"][0]

    answers = {q["id"]: (1 if i < 3 else 0) for i, q in enumerate(z["questions"])}
    result = client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers}).json()
    assert result["score"] == 3 and result["total"] == 5
    assert result["questions"][0]["explanation"].startswith("Because")
    assert [q["correct"] for q in result["questions"]] == [True, True, True, False, False]
    assert client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": answers}).status_code == 409
    assert client.post(f"/api/quizzes/{quiz_id}/confidence", json={"value": 4}).status_code == 200

    progress = client.get("/api/progress").json()
    assert progress["topics"][0]["accuracy"] == 0.6 and progress["mistakes"] == 2
    assert progress["quizzes"][0]["confidence"] == 4

    wrong = [q["id"] for q in result["questions"] if not q["correct"]]
    client.post(f"/api/questions/{wrong[0]}/flag", json={"reason": "answer looks wrong"})
    mistakes = client.post("/api/quizzes", json={"kind": "mistakes"}).json()["id"]
    assert [q["id"] for q in client.get(f"/api/quizzes/{mistakes}").json()["questions"]] == [wrong[1]]
    assert len(llm) == 1


def test_weak_topics(client, llm):
    tid = topic_id(client, "ohms law")
    quiz_id = client.post("/api/quizzes", json={"kind": "topic", "topic_id": tid}).json()["id"]
    qs = client.get(f"/api/quizzes/{quiz_id}").json()["questions"]
    client.post(f"/api/quizzes/{quiz_id}/submit", json={"answers": {q["id"]: 0 for q in qs}})
    assert client.get("/api/progress").json()["weak"][0]["id"] == tid


def test_chapter_test_is_timed_and_covers_topics(client, llm):
    chapter_id = client.get(f"/api/topics/{topic_id(client, 'ohms law')}").json()["chapter_id"]
    quiz_id = client.post("/api/quizzes", json={"kind": "chapter", "chapter_id": chapter_id}).json()["id"]
    z = client.get(f"/api/quizzes/{quiz_id}").json()
    assert z["title"] == "Chapter test: Electricity"
    assert len(z["questions"]) == 10 and z["time_limit_sec"] == 600
    assert len({q["topic_id"] for q in z["questions"]}) == 4
    assert len(llm) == 1 and "4. Heating Effect" in llm[0]


def test_no_mistakes_yet(client):
    r = client.post("/api/quizzes", json={"kind": "mistakes"})
    assert r.status_code == 400 and "No mistakes" in r.json()["detail"]
