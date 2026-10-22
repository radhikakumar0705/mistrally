"""Per-session model choice, last-activity time, and answer sources

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("chat_sessions") as batch:
        batch.add_column(sa.Column("model", sa.String(100), nullable=True))
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    # A session's last activity is its newest message, or its creation time if it has none
    op.execute(
        "UPDATE chat_sessions SET updated_at = COALESCE("
        "(SELECT MAX(h.timestamp) FROM chat_history h WHERE h.session_id = chat_sessions.id), created_at)"
    )

    with op.batch_alter_table("chat_history") as batch:
        batch.add_column(sa.Column("sources", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("chat_history") as batch:
        batch.drop_column("sources")
    with op.batch_alter_table("chat_sessions") as batch:
        batch.drop_column("updated_at")
        batch.drop_column("model")
