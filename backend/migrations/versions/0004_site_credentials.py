"""site_credentials + email_change_tokens

Revision ID: 0004_site_credentials
Revises: 0003_runs_matches
Create Date: 2026-09-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_site_credentials"
down_revision = "0003_runs_matches"
branch_labels = None
depends_on = None

_ts = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "site_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("site", sa.String(20), nullable=False),
        sa.Column("auth_type", sa.String(20), nullable=False, server_default="cookie"),
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("key_version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="unverified"),
        sa.Column("last_verified_at", _ts, nullable=True),
        sa.Column("verify_error", sa.String(400), nullable=False, server_default=""),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_site_credentials_user_id", "site_credentials", ["user_id"])
    op.create_unique_constraint(
        "uq_site_credentials_user_site", "site_credentials", ["user_id", "site"]
    )

    op.create_table(
        "email_change_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("new_email", sa.String(320), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", _ts, nullable=False),
        sa.Column("used_at", _ts, nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_email_change_tokens_user_id", "email_change_tokens", ["user_id"])
    op.create_unique_constraint(
        "uq_email_change_tokens_token_hash", "email_change_tokens", ["token_hash"]
    )


def downgrade() -> None:
    op.drop_table("email_change_tokens")
    op.drop_table("site_credentials")
