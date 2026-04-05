# Database schema (Part 5)

### 1. users
- id: integer primary key
- username: string, unique, not null
- password_hash: string, not null
- created_at: datetime, not null (UTC)

### 2. boards
- id: integer primary key
- user_id: integer foreign key -> users.id
- data_json: text not null (kanban state stringified JSON)
- updated_at: datetime not null (UTC)

### 3. board_updates
- id: integer primary key
- board_id: integer foreign key -> boards.id
- diff_json: text not null (serialized operations or patch)
- created_at: datetime not null (UTC)

### Notes
- SQLite file path: `data/kanban.db` (configurable via env `KANBAN_DB_PATH`).
- Tables are auto-created on backend startup in `backend/app.py`.
