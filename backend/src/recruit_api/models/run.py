"""Run lifecycle + its results: runs, run_steps, run_sources, job_matches, notifications."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


class RunTrigger(enum.StrEnum):
    manual = "manual"
    scheduled = "scheduled"
    api = "api"


class RunStatus(enum.StrEnum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    partial = "partial"
    failed = "failed"
    cancelled = "cancelled"


TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.succeeded, RunStatus.partial, RunStatus.failed, RunStatus.cancelled}
)


class MatchStatus(enum.StrEnum):
    new = "new"
    saved = "saved"
    applied = "applied"
    dismissed = "dismissed"


class Run(Base, TimestampMixin):
    __tablename__ = "runs"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_runs_idempotency_key"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    job_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    trigger: Mapped[RunTrigger] = mapped_column(
        String(16), default=RunTrigger.manual, nullable=False
    )
    status: Mapped[RunStatus] = mapped_column(
        String(16), default=RunStatus.queued, index=True, nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)

    attempt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    worker_id: Mapped[str | None] = mapped_column(String(120))
    report_key: Mapped[str | None] = mapped_column(String(512))
    error_summary: Mapped[str | None] = mapped_column(Text)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL_RUN_STATUSES


class RunStep(Base, TimestampMixin):
    __tablename__ = "run_steps"

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RunSource(Base, TimestampMixin):
    __tablename__ = "run_sources"
    __table_args__ = (UniqueConstraint("run_id", "source", name="uq_run_sources_run_source"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)


class JobMatch(Base, TimestampMixin):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint("user_id", "external_hash", name="uq_job_matches_user_hash"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), index=True
    )
    job_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("job_profiles.id", ondelete="SET NULL"), index=True
    )

    external_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
    company: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    description_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    salary: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    posted_date: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    match_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matched_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    missing_skills: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}", nullable=False
    )
    why_fit: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[str] = mapped_column(String(12), nullable=False, default="LOW")
    recommended_action: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    matched_profile_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    status: Mapped[MatchStatus] = mapped_column(
        String(12), default=MatchStatus.new, index=True, nullable=False
    )
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id", ondelete="SET NULL"), index=True
    )
    channel: Mapped[str] = mapped_column(String(20), default="email", nullable=False)
    to_addr: Mapped[str] = mapped_column(String(320), nullable=False)
    subject: Mapped[str] = mapped_column(String(400), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(200))
