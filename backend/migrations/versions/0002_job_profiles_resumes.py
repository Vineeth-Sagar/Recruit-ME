"""job_profiles + resumes + resume_parses

Revision ID: 0002_job_profiles_resumes
Revises: 0001_users_auth
Create Date: 2026-09-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_job_profiles_resumes"
down_revision = "0001_users_auth"
branch_labels = None
depends_on = None

_ts = sa.DateTime(timezone=True)
_txt_arr = postgresql.ARRAY(sa.Text())


def upgrade() -> None:
    op.create_table(
        "job_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("target_roles", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("locations", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("job_types", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("must_have_skills", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("nice_to_have_skills", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("exclude_companies", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("watchlist_companies", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("min_match_percent", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("min_salary", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("big3_optin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("schedule_cron", sa.String(120), nullable=True),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_profiles_user_id", "job_profiles", ["user_id"])

    op.create_table(
        "resumes",
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
            sa.ForeignKey("job_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False, server_default="application/pdf"),
        sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
        sa.Column("parse_error", sa.Text(), nullable=True),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resumes_user_id", "resumes", ["user_id"])
    op.create_index("ix_resumes_job_profile_id", "resumes", ["job_profile_id"])
    op.create_index("ix_resumes_content_sha256", "resumes", ["content_sha256"])

    op.create_table(
        "resume_parses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resume_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("parsed_json", postgresql.JSONB(), nullable=False),
        sa.Column("skills", _txt_arr, nullable=False, server_default="{}"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", _ts, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _ts, server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_parses_resume_id", "resume_parses", ["resume_id"])


def downgrade() -> None:
    op.drop_table("resume_parses")
    op.drop_table("resumes")
    op.drop_table("job_profiles")
