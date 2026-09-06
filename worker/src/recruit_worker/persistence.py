"""Write an ``EngineResult`` to the database and (once) notify the user.

Every write is idempotent so a retried run resumes cleanly:
- ``run_sources`` upsert on ``(run_id, source)``
- ``job_matches`` insert ``ON CONFLICT (user_id, external_hash) DO NOTHING``
- the email is guarded by ``runs.notified_at``
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from recruit_api.models.run import JobMatch, Notification, Run, RunSource, RunStep
from recruit_api.models.user import User
from recruit_engine.email_templates import build_report_email_html, build_report_subject
from recruit_engine.report import build_report
from recruit_engine.types import EngineResult
from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _now() -> datetime:
    return datetime.now(UTC)


async def clear_steps(db: AsyncSession, run_id: uuid.UUID) -> None:
    await db.execute(delete(RunStep).where(RunStep.run_id == run_id))


async def persist_step(
    db: AsyncSession, run_id: uuid.UUID, name: str, status: str, detail: dict
) -> None:
    db.add(RunStep(run_id=run_id, name=name, status=status, detail=detail, at=_now()))
    await db.flush()


async def save_result(db: AsyncSession, run: Run, result: EngineResult) -> int:
    for source, info in result.per_source.items():
        stmt = pg_insert(RunSource).values(
            run_id=run.id,
            source=source,
            status=info.get("status", "unknown"),
            jobs_found=info.get("found", 0),
            latency_ms=info.get("latency_ms", 0),
            error=info.get("error"),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_run_sources_run_source",
            set_={
                "status": stmt.excluded.status,
                "jobs_found": stmt.excluded.jobs_found,
                "latency_ms": stmt.excluded.latency_ms,
                "error": stmt.excluded.error,
            },
        )
        await db.execute(stmt)

    inserted = 0
    for m in result.matched:
        j = m.job
        stmt = (
            pg_insert(JobMatch)
            .values(
                user_id=run.user_id,
                run_id=run.id,
                job_profile_id=run.job_profile_id,
                external_hash=j.external_hash,
                source=j.source[:60],
                company=j.company[:300],
                title=j.title[:400],
                location=j.location[:200],
                url=j.url[:1024],
                description_excerpt=(j.description or "")[:2000],
                salary=(j.salary or "")[:120],
                posted_date=(j.posted_date or "")[:40],
                match_percentage=m.match_percentage,
                matched_skills=list(m.matched_skills),
                missing_skills=list(m.missing_skills),
                why_fit=m.why_fit[:4000],
                urgency=(m.urgency or "LOW")[:12],
                recommended_action=(m.recommended_action or "")[:40],
                matched_profile_id=(m.matched_profile_id or "")[:64],
            )
            .on_conflict_do_nothing(constraint="uq_job_matches_user_hash")
        )
        res = await db.execute(stmt)
        inserted += res.rowcount or 0  # type: ignore[attr-defined]

    sources = result.per_source.values()
    run.stats = {
        "scraped": result.scraped,
        "new": result.new,
        "matched": len(result.matched),
        "inserted": inserted,
        "sources_ok": sum(1 for i in sources if i.get("status") == "ok"),
        "sources_failed": sum(1 for i in sources if i.get("status") == "failed"),
        "ai_degraded": result.ai_degraded,
        "top_missing_skills": sorted(result.missing_skills_tally.items(), key=lambda kv: -kv[1])[
            :15
        ],
    }
    await db.flush()
    return inserted


def _match_row(m: JobMatch) -> dict:
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


async def notify_if_needed(db: AsyncSession, run: Run, *, email_sender, object_store) -> bool:
    """Build the report from *all* of this run's matches, upload it, and email
    the user — at most once per run. Returns True if a notification was sent."""
    if run.notified_at is not None:
        return False

    rows = list(
        await db.scalars(
            select(JobMatch)
            .where(JobMatch.run_id == run.id)
            .order_by(JobMatch.match_percentage.desc())
        )
    )
    if not rows:
        return False

    dicts = [_match_row(m) for m in rows]
    report = build_report(dicts, [], str(run.job_profile_id), tips=[])
    key = f"reports/{run.user_id}/{run.id}.xlsx"
    await object_store.put(key, report, content_type=_XLSX_MIME)
    run.report_key = key

    user = await db.get(User, run.user_id)
    if user is None:
        return False
    subject = build_report_subject(dicts)
    html = build_report_email_html(dicts, _now().strftime("%B %d, %Y"))
    await email_sender.send(to=user.email, subject=subject, html=html)

    db.add(
        Notification(
            user_id=run.user_id,
            run_id=run.id,
            channel="email",
            to_addr=user.email,
            subject=subject[:400],
            status="sent",
        )
    )
    run.notified_at = _now()
    await db.flush()
    return True
