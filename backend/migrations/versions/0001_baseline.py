"""Baseline: users and chat history, as in the first release

Databases created by older versions already have these tables, so they are
only created when missing. That lets `flask db upgrade` adopt an existing database.

Revision ID: 0001
Revises:
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    tables = sa.inspect(op.get_bind()).get_table_names()

    if "user" not in tables:
        op.create_table(
            "user",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("username", sa.String(50), nullable=False, unique=True),
            sa.Column("email", sa.String(120), nullable=False, unique=True),
            sa.Column("password", sa.String(200), nullable=False),
        )

    if "chat_history" not in tables:
        op.create_table(
            "chat_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("user_message", sa.Text(), nullable=False),
            sa.Column("bot_response", sa.Text(), nullable=False),
            sa.Column("timestamp", sa.DateTime()),
        )


def downgrade():
    op.drop_table("chat_history")
    op.drop_table("user")
