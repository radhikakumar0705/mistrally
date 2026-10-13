"""
One-time upgrade for databases created before chat sessions existed.

Creates the chat_sessions table, adds chat_history.session_id, and moves each
user's existing messages into an "Earlier chats" session. Safe to run twice.

Usage (from backend/):  python migrate_add_sessions.py
"""
from sqlalchemy import inspect, text

from app import app  # creating the app creates any missing tables (chat_sessions)
from extensions import db

LEGACY_TITLE = "Earlier chats"


def migrate():
    with app.app_context():
        engine = db.engine
        columns = [c["name"] for c in inspect(engine).get_columns("chat_history")]
        if "session_id" in columns:
            print("chat_history already has session_id; nothing to do.")
            return

        with engine.begin() as conn:
            orphans = conn.execute(text(
                "SELECT COUNT(*) FROM chat_history WHERE user_id NOT IN (SELECT id FROM user)"
            )).scalar()
            if orphans:
                raise SystemExit(
                    f"{orphans} chat_history rows belong to users that no longer exist. "
                    "Delete or reassign them, then run this again. Nothing was changed."
                )

            conn.execute(text("ALTER TABLE chat_history ADD COLUMN session_id INTEGER NULL"))

            user_ids = [row[0] for row in conn.execute(text("SELECT DISTINCT user_id FROM chat_history"))]
            for user_id in user_ids:
                first = conn.execute(
                    text("SELECT MIN(timestamp) FROM chat_history WHERE user_id = :u"), {"u": user_id}
                ).scalar()
                result = conn.execute(
                    text("INSERT INTO chat_sessions (user_id, title, created_at) VALUES (:u, :t, :c)"),
                    {"u": user_id, "t": LEGACY_TITLE, "c": first},
                )
                conn.execute(
                    text("UPDATE chat_history SET session_id = :s WHERE user_id = :u"),
                    {"s": result.lastrowid, "u": user_id},
                )

            if engine.dialect.name == "mysql":
                conn.execute(text(
                    "ALTER TABLE chat_history "
                    "MODIFY session_id INTEGER NOT NULL, "
                    "ADD INDEX ix_chat_history_session_id (session_id), "
                    "ADD CONSTRAINT fk_chat_history_session "
                    "FOREIGN KEY (session_id) REFERENCES chat_sessions (id)"
                ))

        print(f"Moved messages for {len(user_ids)} user(s) into '{LEGACY_TITLE}' sessions.")


if __name__ == "__main__":
    migrate()
