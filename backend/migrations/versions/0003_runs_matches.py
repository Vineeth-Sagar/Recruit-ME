"""runs + run_steps + run_sources + job_matches + notifications

Revision ID: 0003_runs_matches
Revises: 0002_job_profiles_resumes
Create Date: 2026-09-06
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_runs_matches"
down_revision = "0002_job_profiles_resumes"
branch_labels = None
depends_on = None

_ts = sa.DateTime(timezone=True)
_txt_arr = postgresql.ARRAY(sa.Text())


def upgrade() -> None:
    op.add_column(
        "job_profiles",
        sa.Column(
            "enabled_sources",
            _txt_arr,
            nullable=False,
            server_default="{wellfound,yc,hackernews,jobspy}",
        ),
    )

    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("queued_at", _ts, nullable=True),
        sa.Column("started_at", _ts, nullable=True),
        sa.Column("finished_at", _ts, nullable=True),
        sa.Column("notified_at", _ts, nullable=True),
        sa.Column("worker_id", sa.String(120), nullable=True),
        sa.Column("report_key", sa.String(512), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.Column("stats", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_runs_user_id", "runs", ["user_id"])
    op.create_index("ix_runs_job_profile_id", "runs", ["job_profile_id"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_unique_constraint("uq_runs_idempotency_key", "runs", ["idempotency_key"])

    op.create_table(
        "run_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("at", _ts, nullable=False),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_steps_run_id", "run_steps", ["run_id"])

    op.create_table(
        "run_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_run_sources_run_id", "run_sources", ["run_id"])
    op.create_unique_constraint("uq_run_sources_run_source", "run_sources", ["run_id", "source"])

    op.create_table(
        "job_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "job_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("job_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_hash", sa.String(64), nullable=False),
        sa.Column("source", sa.String(60), nullable=False),
        sa.Column("company", sa.String(300), nullable=False, server_default=""),
        sa.Column("title", sa.String(400), nullable=False, server_default=""),
        sa.Column("location", sa.String(200), nullable=False, server_default=""),
        sa.Column("url", sa.String(1024), nullable=False, server_default=""),
        sa.Column("description_excerpt", sa.Text(), nullable=False, server_default=""),
        sa.Column("salary", sa.String(120), nullable=False, server_default=""),
        sa.Column("posted_date", sa.String(40), nullable=False, server_default=""),
        sa.Column("match_percentage", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_skills", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("missing_skills", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("why_fit", sa.Text(), nullable=False, server_default=""),
        sa.Column("urgency", sa.String(12), nullable=False, server_default="LOW"),
        sa.Column("recommended_action", sa.String(40), nullable=False, server_default=""),
        sa.Column("matched_profile_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(12), nullable=False, server_default="new"),
        sa.Column("applied_at", _ts, nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_matches_user_id", "job_matches", ["user_id"])
    op.create_index("ix_job_matches_run_id", "job_matches", ["run_id"])
    op.create_index("ix_job_matches_job_profile_id", "job_matches", ["job_profile_id"])
    op.create_index("ix_job_matches_status", "job_matches", ["status"])
    op.create_unique_constraint(
        "uq_job_matches_user_hash", "job_matches", ["user_id", "external_hash"]
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(20), nullable=False, server_default="email"),
        sa.Column("to_addr", sa.String(320), nullable=False),
        sa.Column("subject", sa.String(400), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("provider_message_id", sa.String(200), nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_run_id", "notifications", ["run_id"])


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("job_matches")
    op.drop_table("run_sources")
    op.drop_table("run_steps")
    op.drop_table("runs")
    op.drop_column("job_profiles", "enabled_sources")
