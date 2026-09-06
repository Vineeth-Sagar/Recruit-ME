"""recruit_worker.tasks.execute_run — happy path, idempotent re-delivery, retry, partial."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import pytest
from arq import Retry
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.resume import Resume, ResumeParse, ResumeStatus
from recruit_api.models.run import JobMatch, Notification, Run, RunStatus, RunStep
from recruit_engine.types import JobPosting
from recruit_worker.tasks.execute_run import execute_run
from sqlalchemy import select

pytestmark = pytest.mark.asyncio


async def _seed(db, make_user, *, email="run@example.com", min_match=50, sources=("yc",)):
    user = await make_user(email)
    profile = JobProfile(
        user_id=user.id,
        name="P",
        target_roles=["Backend Engineer"],
        locations=["Bengaluru"],
        min_match_percent=min_match,
        enabled_sources=list(sources),
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    resume = Resume(
        user_id=user.id,
        job_profile_id=profile.id,
        original_filename="cv.pdf",
        storage_key="k",
        content_sha256="h",
        size_bytes=1,
        status=ResumeStatus.parsed,
    )
    db.add(resume)
    await db.flush()
    db.add(
        ResumeParse(
            resume_id=resume.id,
            model="m",
            parsed_json={"technical_skills": ["Python"]},
            skills=["Python"],
        )
    )
    run = Run(
        user_id=user.id,
        job_profile_id=profile.id,
        status=RunStatus.queued,
        idempotency_key=f"t:{uuid.uuid4().hex}",
        queued_at=datetime.now(UTC),
    )
    db.add(run)
    await db.flush()
    return user, profile, run


def _fake_source(*jobs: JobPosting):
    async def _f(spec, cred, rl, *, timeout_s):
        return list(jobs)

    return _f


async def test_happy_path(execute_run_ctx, db_session, make_user, monkeypatch):
    _, _, run = await _seed(db_session, make_user)
    job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")
    monkeypatch.setattr("recruit_engine.engine.SCRAPERS", {"yc": _fake_source(job)})
    execute_run_ctx["llm"].reply = json.dumps(
        {
            "0": {
                "match_percentage": 88,
                "why_good_fit": "great",
                "urgency": "HIGH",
                "missing_skills": ["Kafka"],
            }
        }
    )

    await execute_run(execute_run_ctx, str(run.id))

    await db_session.refresh(run)
    assert run.status == RunStatus.succeeded
    assert run.started_at and run.finished_at and run.notified_at
    assert run.stats["matched"] == 1 and run.stats["scraped"] == 1

    matches = list(await db_session.scalars(select(JobMatch).where(JobMatch.run_id == run.id)))
    assert [m.company for m in matches] == ["Acme"]
    assert matches[0].match_percentage == 88

    steps = list(await db_session.scalars(select(RunStep).where(RunStep.run_id == run.id)))
    assert {s.name for s in steps} >= {"scrape:yc", "dedupe", "match", "report"}

    assert len(execute_run_ctx["email_sender"].sent) == 1
    assert run.report_key and await execute_run_ctx["object_store"].get(run.report_key)


async def test_idempotent_redelivery_is_a_noop(execute_run_ctx, db_session, make_user, monkeypatch):
    _, _, run = await _seed(db_session, make_user, email="idem@example.com")
    job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")
    monkeypatch.setattr("recruit_engine.engine.SCRAPERS", {"yc": _fake_source(job)})
    execute_run_ctx["llm"].reply = json.dumps({"0": {"match_percentage": 80, "why_good_fit": "y"}})

    await execute_run(execute_run_ctx, str(run.id))
    await db_session.refresh(run)
    assert run.status == RunStatus.succeeded
    assert len(execute_run_ctx["email_sender"].sent) == 1

    # re-deliver the same job id
    await execute_run(execute_run_ctx, str(run.id))
    await db_session.refresh(run)
    assert run.status == RunStatus.succeeded
    assert len(execute_run_ctx["email_sender"].sent) == 1  # no second email
    n = await db_session.scalar(select(Notification).where(Notification.run_id == run.id))
    assert n is not None


async def test_transient_failure_retries_then_completes_with_one_email(
    execute_run_ctx, db_session, make_user, monkeypatch
):
    _, _, run = await _seed(db_session, make_user, email="retry@example.com")
    job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")
    monkeypatch.setattr("recruit_engine.engine.SCRAPERS", {"yc": _fake_source(job)})
    execute_run_ctx["llm"].reply = json.dumps({"0": {"match_percentage": 77, "why_good_fit": "y"}})

    calls = {"n": 0}
    real_put = execute_run_ctx["object_store"].put

    async def flaky_put(key, data, *, content_type):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("s3 connection reset")
        return await real_put(key, data, content_type=content_type)

    execute_run_ctx["object_store"].put = flaky_put

    with pytest.raises(Retry):
        await execute_run(execute_run_ctx, str(run.id))

    await db_session.refresh(run)
    assert run.status == RunStatus.queued
    assert run.attempt == 1
    # matches were persisted on attempt 1 before the notify step blew up
    assert await db_session.scalar(select(JobMatch).where(JobMatch.run_id == run.id)) is not None
    assert execute_run_ctx["email_sender"].sent == []

    # attempt 2
    await execute_run(execute_run_ctx, str(run.id))
    await db_session.refresh(run)
    assert run.status == RunStatus.succeeded
    assert run.attempt == 2
    assert len(execute_run_ctx["email_sender"].sent) == 1


async def test_partial_when_a_source_fails(execute_run_ctx, db_session, make_user, monkeypatch):
    _, _, run = await _seed(
        db_session, make_user, email="partial@example.com", sources=("yc", "wellfound")
    )
    job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")

    async def boom(spec, cred, rl, *, timeout_s):
        raise RuntimeError("wellfound down")

    monkeypatch.setattr(
        "recruit_engine.engine.SCRAPERS", {"yc": _fake_source(job), "wellfound": boom}
    )
    execute_run_ctx["llm"].reply = json.dumps({"0": {"match_percentage": 90, "why_good_fit": "y"}})

    await execute_run(execute_run_ctx, str(run.id))
    await db_session.refresh(run)
    assert run.status == RunStatus.partial
    assert run.stats["sources_failed"] == 1


async def test_no_matches_no_email(execute_run_ctx, db_session, make_user, monkeypatch):
    _, _, run = await _seed(db_session, make_user, email="empty@example.com", min_match=95)
    job = JobPosting(source="YC", company="Acme", title="Backend Engineer", description="Python")
    monkeypatch.setattr("recruit_engine.engine.SCRAPERS", {"yc": _fake_source(job)})
    execute_run_ctx["llm"].reply = json.dumps({"0": {"match_percentage": 30, "why_good_fit": "no"}})

    await execute_run(execute_run_ctx, str(run.id))
    await db_session.refresh(run)
    assert run.status == RunStatus.succeeded
    assert run.notified_at is None
    assert execute_run_ctx["email_sender"].sent == []
