"""A tenant's job profile — target roles, filters, schedule."""

from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, uuid_pk


def _str_array() -> Mapped[list[str]]:
    return mapped_column(ARRAY(Text), nullable=False, default=list, server_default="{}")


class JobProfile(Base, TimestampMixin):
    __tablename__ = "job_profiles"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    target_roles: Mapped[list[str]] = _str_array()
    locations: Mapped[list[str]] = _str_array()
    job_types: Mapped[list[str]] = _str_array()
    must_have_skills: Mapped[list[str]] = _str_array()
    nice_to_have_skills: Mapped[list[str]] = _str_array()
    exclude_companies: Mapped[list[str]] = _str_array()
    watchlist_companies: Mapped[list[str]] = _str_array()

    min_match_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    min_salary: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # LinkedIn / Indeed / Glassdoor only run for a profile that has opted in.
    # The consent UI that flips this lands in Phase 4.6.
    big3_optin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    schedule_cron: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
