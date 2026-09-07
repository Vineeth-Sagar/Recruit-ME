"""Per-tenant run idempotency + normalise unique constraints to unique indexes.

Revision ID: 0005_run_idempotency_indexes
Revises: 0004_site_credentials
Create Date: 2026-09-07
"""

from __future__ import annotations

from alembic import op

revision = "0005_run_idempotency_indexes"
down_revision = "0004_site_credentials"
branch_labels = None
depends_on = None

# (table, column) whose uniqueness lives in a named constraint + (sometimes) a
# redundant plain index. The ORM models want a single unique index `ix_<t>_<c>`.
_UNIQUE_COLS = [
    ("users", "email"),
    ("refresh_tokens", "token_hash"),
    ("email_verification_tokens", "token_hash"),
    ("password_reset_tokens", "token_hash"),
    ("email_change_tokens", "token_hash"),
]


def upgrade() -> None:
    # ── per-tenant run idempotency key ───────────────────────────────
    op.drop_constraint("uq_runs_idempotency_key", "runs", type_="unique")
    op.create_unique_constraint(
        "uq_runs_user_idempotency_key", "runs", ["user_id", "idempotency_key"]
    )

    # ── unique constraint -> unique index ───────────────────────────
    for table, col in _UNIQUE_COLS:
        op.drop_constraint(f"uq_{table}_{col}", table, type_="unique")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_{col}")
        op.create_index(f"ix_{table}_{col}", table, [col], unique=True)


def downgrade() -> None:
    for table, col in _UNIQUE_COLS:
        op.drop_index(f"ix_{table}_{col}", table_name=table)
        op.create_unique_constraint(f"uq_{table}_{col}", table, [col])
        op.create_index(f"ix_{table}_{col}", table, [col])

    op.drop_constraint("uq_runs_user_idempotency_key", "runs", type_="unique")
    op.create_unique_constraint("uq_runs_idempotency_key", "runs", ["idempotency_key"])
