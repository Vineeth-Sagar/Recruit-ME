"""Build the 4-sheet Excel export from a tenant's job matches."""

from __future__ import annotations

import uuid

from recruit_engine.report import build_report
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.run import JobMatch, MatchStatus

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _row(m: JobMatch) -> dict:
    return {
        "company": m.company,
        "title": m.title,
        "match_percentage": m.match_percentage,
        "matched_profile": m.matched_profile_id,
        "urgency": m.urgency,
        "apply_url": m.url,
        "location": m.location,
        "salary": m.salary,
        "company_type": "",
        "company_size": "",
        "matched_skills": list(m.matched_skills),
        "missing_skills": list(m.missing_skills),
        "why_good_fit": m.why_fit,
        "posted_date": m.posted_date,
        "source": m.source,
    }


async def build_matches_xlsx(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    run: uuid.UUID | None = None,
    profile: uuid.UUID | None = None,
    match_status: MatchStatus | None = None,
    min_match: int = 0,
    q: str | None = None,
) -> bytes:
    where = [JobMatch.user_id == user_id, JobMatch.match_percentage >= min_match]
    if run is not None:
        where.append(JobMatch.run_id == run)
    if profile is not None:
        where.append(JobMatch.job_profile_id == profile)
    if match_status is not None:
        where.append(JobMatch.status == match_status)
    if q:
        like = f"%{q}%"
        where.append(or_(JobMatch.company.ilike(like), JobMatch.title.ilike(like)))

    rows = list(
        await db.scalars(select(JobMatch).where(*where).order_by(JobMatch.match_percentage.desc()))
    )
    return build_report([_row(m) for m in rows], [], "export", tips=[])
