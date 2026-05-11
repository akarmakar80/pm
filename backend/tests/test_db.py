import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db


@pytest.fixture(autouse=True)
def use_temp_db(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    monkeypatch.setenv('KANBAN_DB_PATH', tmp.name)
    db.init_db()
    yield
    os.remove(tmp.name)


def test_db_schema_and_insert_and_retrieve():
    user_id = db.create_user('user', 'hashed-password')
    board_json = json.dumps({'columns': []})
    board_id = db.create_board(user_id, board_json)

    loaded_board = db.get_board_by_user(user_id)
    assert loaded_board is not None
    assert loaded_board['user_id'] == user_id
    assert loaded_board['data_json'] == board_json

    update_id = db.add_board_update(board_id, json.dumps({'change': 'test'}))
    assert isinstance(update_id, int)

    assert db.count_users() == 1
    assert db.count_boards() == 1

