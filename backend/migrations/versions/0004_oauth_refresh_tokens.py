"""Google sign-in fields on users, and refresh tokens for rotation and revocation

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user") as batch:
        batch.alter_column("password", existing_type=sa.String(200), nullable=True)
        batch.add_column(sa.Column("google_sub", sa.String(255), nullable=True))
        batch.add_column(sa.Column("name", sa.String(120), nullable=True))
        batch.add_column(sa.Column("avatar_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("created_at", sa.DateTime(), nullable=True))
        batch.create_unique_constraint("uq_user_google_sub", ["google_sub"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id", name="fk_refresh_tokens_user_id"),
                  nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by", sa.String(64), nullable=True),
    )
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade():
    op.drop_table("refresh_tokens")
    with op.batch_alter_table("user") as batch:
        batch.drop_constraint("uq_user_google_sub", type_="unique")
        batch.drop_column("created_at")
        batch.drop_column("avatar_url")
        batch.drop_column("name")
        batch.drop_column("google_sub")
        batch.alter_column("password", existing_type=sa.String(200), nullable=False)
