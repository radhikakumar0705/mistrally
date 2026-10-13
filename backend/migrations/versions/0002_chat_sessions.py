"""Chat sessions: group messages into conversations

Existing messages are moved into one "Earlier chats" session per user.
Skips work that a database created by `db.create_all()` already has.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

LEGACY_TITLE = "Earlier chats"


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "chat_sessions" not in inspector.get_table_names():
        op.create_table(
            "chat_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", name="fk_chat_sessions_user_id"),
                      nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime()),
        )
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    if "session_id" in [c["name"] for c in inspector.get_columns("chat_history")]:
        return

    orphans = bind.execute(sa.text(
        "SELECT COUNT(*) FROM chat_history WHERE user_id NOT IN (SELECT id FROM user)"
    )).scalar()
    if orphans:
        raise RuntimeError(
            f"{orphans} chat_history rows belong to users that no longer exist. "
            "Delete or reassign them, then run the upgrade again."
        )

    with op.batch_alter_table("chat_history") as batch:
        batch.add_column(sa.Column("session_id", sa.Integer(), nullable=True))

    sessions = sa.table(
        "chat_sessions",
        sa.column("id", sa.Integer), sa.column("user_id", sa.Integer),
        sa.column("title", sa.String), sa.column("created_at", sa.DateTime),
    )
    history = sa.table(
        "chat_history",
        sa.column("user_id", sa.Integer), sa.column("session_id", sa.Integer),
        sa.column("timestamp", sa.DateTime),
    )
    first_message = (
        sa.select(history.c.user_id, sa.func.min(history.c.timestamp))
        .group_by(history.c.user_id)
    )
    for user_id, first_at in bind.execute(first_message).all():
        result = bind.execute(sessions.insert().values(user_id=user_id, title=LEGACY_TITLE, created_at=first_at))
        bind.execute(
            history.update().where(history.c.user_id == user_id)
            .values(session_id=result.lastrowid)
        )

    with op.batch_alter_table("chat_history") as batch:
        batch.alter_column("session_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_chat_history_session_id", "chat_sessions", ["session_id"], ["id"])
        batch.create_foreign_key("fk_chat_history_user_id", "user", ["user_id"], ["id"])
        batch.create_index("ix_chat_history_session_id", ["session_id"])
        batch.create_index("ix_chat_history_user_id", ["user_id"])


def downgrade():
    with op.batch_alter_table("chat_history") as batch:
        batch.drop_index("ix_chat_history_user_id")
        batch.drop_index("ix_chat_history_session_id")
        batch.drop_constraint("fk_chat_history_user_id", type_="foreignkey")
        batch.drop_constraint("fk_chat_history_session_id", type_="foreignkey")
        batch.drop_column("session_id")
    op.drop_table("chat_sessions")
