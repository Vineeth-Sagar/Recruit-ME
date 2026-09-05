"""users + auth tokens

Revision ID: 0001_users_auth
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_users_auth"
down_revision = None
branch_labels = None
depends_on = None

_ts = sa.DateTime(timezone=True)


def _one_time_token_table(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", _ts, nullable=False),
        sa.Column("used_at", _ts, nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(f"ix_{name}_user_id", name, ["user_id"])
    op.create_unique_constraint(f"uq_{name}_token_hash", name, ["token_hash"])
    op.create_index(f"ix_{name}_token_hash", name, ["token_hash"])


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(200), nullable=False, server_default=""),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("plan", sa.String(20), nullable=False, server_default="free"),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_verification"),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", _ts, nullable=False),
        sa.Column("revoked_at", _ts, nullable=True),
        sa.Column(
            "rotated_from_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("refresh_tokens.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_agent", sa.String(400), nullable=False, server_default=""),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_unique_constraint("uq_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    _one_time_token_table("email_verification_tokens")
    _one_time_token_table("password_reset_tokens")


def downgrade() -> None:
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
