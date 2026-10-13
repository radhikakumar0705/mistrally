import sqlite3

import sqlalchemy as sa
from conftest import make_config
from flask_migrate import upgrade

from app import create_app
from extensions import db

LEGACY_SCHEMA = """
CREATE TABLE user (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE,
                   email VARCHAR(120) NOT NULL UNIQUE, password VARCHAR(200) NOT NULL);
CREATE TABLE chat_history (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, user_message TEXT NOT NULL,
                           bot_response TEXT NOT NULL, timestamp DATETIME);
INSERT INTO user VALUES (1, 'a', 'a@x.io', 'h'), (2, 'b', 'b@x.io', 'h');
INSERT INTO chat_history VALUES (1, 1, 'hi', 'hello', '2025-01-01 10:00:00'),
                                (2, 1, 'q', 'r', '2025-01-02 10:00:00'),
                                (3, 2, 'yo', 'hey', '2025-01-03 10:00:00');
"""


def assert_schema_matches_models():
    inspector = sa.inspect(db.engine)
    for table in db.metadata.sorted_tables:
        actual = {c["name"] for c in inspector.get_columns(table.name)}
        assert actual == set(table.columns.keys()), table.name


def test_upgrade_creates_schema_from_scratch(tmp_path):
    app = create_app(make_config(tmp_path))
    with app.app_context():
        upgrade()
        assert_schema_matches_models()


def test_upgrade_adopts_legacy_database_and_keeps_messages(tmp_path):
    with sqlite3.connect(tmp_path / "test.db") as conn:
        conn.executescript(LEGACY_SCHEMA)

    app = create_app(make_config(tmp_path))
    with app.app_context():
        upgrade()
        assert_schema_matches_models()
        sessions = db.session.execute(sa.text(
            "SELECT id, user_id, title, created_at, updated_at FROM chat_sessions ORDER BY user_id"
        )).all()
        assert [(s.user_id, s.title) for s in sessions] == [(1, "Earlier chats"), (2, "Earlier chats")]
        assert str(sessions[0].created_at).startswith("2025-01-01")
        assert str(sessions[0].updated_at).startswith("2025-01-02")

        history = db.session.execute(sa.text("SELECT id, session_id FROM chat_history ORDER BY id")).all()
        assert [h.session_id for h in history] == [sessions[0].id, sessions[0].id, sessions[1].id]


def test_upgrade_adopts_database_made_by_create_all(tmp_path):
    """Databases from the previous version were created with db.create_all() and the sessions schema."""
    with sqlite3.connect(tmp_path / "test.db") as conn:
        conn.executescript("""
            CREATE TABLE user (id INTEGER PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE,
                               email VARCHAR(120) NOT NULL UNIQUE, password VARCHAR(200) NOT NULL);
            CREATE TABLE chat_sessions (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES user(id),
                                        title VARCHAR(255) NOT NULL, created_at DATETIME);
            CREATE TABLE chat_history (id INTEGER PRIMARY KEY,
                                       session_id INTEGER NOT NULL REFERENCES chat_sessions(id),
                                       user_id INTEGER NOT NULL REFERENCES user(id), user_message TEXT NOT NULL,
                                       bot_response TEXT NOT NULL, timestamp DATETIME);
            INSERT INTO user VALUES (1, 'a', 'a@x.io', 'h');
            INSERT INTO chat_sessions VALUES (7, 1, 'Recursion', '2025-02-01 09:00:00');
            INSERT INTO chat_history VALUES (1, 7, 1, 'hi', 'hello', '2025-02-01 09:05:00');
        """)

    app = create_app(make_config(tmp_path))
    with app.app_context():
        upgrade()
        assert_schema_matches_models()
        row = db.session.execute(sa.text("SELECT title, updated_at FROM chat_sessions WHERE id = 7")).one()
        assert row.title == "Recursion"
        assert str(row.updated_at).startswith("2025-02-01 09:05")
