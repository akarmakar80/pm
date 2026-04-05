import os
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def get_db_path():
    return os.getenv("KANBAN_DB_PATH", str(BASE_DIR.parent / "data" / "kanban.db"))


# Ensure data folder exists for default path
default_db = get_db_path()
(Path(default_db).parent).mkdir(parents=True, exist_ok=True)


def get_connection():
    db_path = get_db_path()
    (Path(db_path).parent).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            data_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS board_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL,
            diff_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(board_id) REFERENCES boards(id)
        )
        """
    )

    conn.commit()
    conn.close()


def create_user(username: str, password_hash: str):
    created_at = datetime.utcnow().isoformat() + "Z"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, created_at),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def create_board(user_id: int, data_json: str):
    updated_at = datetime.utcnow().isoformat() + "Z"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO boards (user_id, data_json, updated_at) VALUES (?, ?, ?)",
        (user_id, data_json, updated_at),
    )
    board_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return board_id


def add_board_update(board_id: int, diff_json: str):
    created_at = datetime.utcnow().isoformat() + "Z"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO board_updates (board_id, diff_json, created_at) VALUES (?, ?, ?)",
        (board_id, diff_json, created_at),
    )
    update_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return update_id


def get_board(board_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards WHERE id = ?", (board_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_user(username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_board_by_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM boards WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_board(board_id: int, data_json: str):
    updated_at = datetime.utcnow().isoformat() + "Z"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE boards SET data_json = ?, updated_at = ? WHERE id = ?",
        (data_json, updated_at, board_id),
    )
    conn.commit()
    conn.close()
    return board_id


def count_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM users")
    n = cursor.fetchone()[0]
    conn.close()
    return n


def count_boards():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as c FROM boards")
    n = cursor.fetchone()[0]
    conn.close()
    return n
