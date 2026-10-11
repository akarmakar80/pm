import json
from pathlib import Path

from safety import is_blocked

SEED = Path(__file__).resolve().parent.parent / "seed"


def test_syllabus_terms_are_never_blocked():
    for subject in json.loads((SEED / "syllabus.json").read_text())["subjects"]:
        for chapter in subject["chapters"]:
            for topic in chapter["topics"]:
                assert not is_blocked(f"{chapter['title']} {topic['title']} {topic['keywords']}"), topic


def test_blocked_terms():
    assert is_blocked("watch porn")
    assert is_blocked("Online BETTING tips")
    assert not is_blocked("seen with the naked eye")
    assert not is_blocked("sexual reproduction in flowering plants")
