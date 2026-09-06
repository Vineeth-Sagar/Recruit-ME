"""enqueue_due_runs — cron matching + single-run guarantee under concurrency."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from recruit_api.models.job_profile import JobProfile
from recruit_api.models.run import Run, RunTrigger
from recruit_worker.scheduler import _is_due, enqueue_due_runs
from sqlalchemy import func, select


def test_is_due_matches_the_minute():
    now = datetime(2026, 9, 6, 7, 0, tzinfo=UTC)
    assert _is_due("0 7 * * *", "UTC", now) is True
    assert _is_due("0 8 * * *", "UTC", now) is False
    # 07:00 UTC == 12:30 IST
    assert _is_due("30 12 * * *", "Asia/Kolkata", now) is True


async def _due_profile(db, make_user, cron="* * * * *"):
    user = await make_user(f"sched-{datetime.now(UTC).timestamp()}@example.com")
    p = JobProfile(
        user_id=user.id,
        name="P",
        target_roles=["x"],
        locations=["y"],
        is_active=True,
        schedule_cron=cron,
        timezone="UTC",
    )
    db.add(p)
    await db.flush()
    return p


async def test_enqueues_one_run_for_a_due_profile(
    db_session, shared_sessionmaker, redis_client, make_user
):
    p = await _due_profile(db_session, make_user)
    enqueued: list[tuple] = []

    async def _enqueue(fn, *args):
        enqueued.append((fn, *args))

    ctx = {"sessionmaker": shared_sessionmaker, "redis": redis_client, "enqueue": _enqueue}

    n = await enqueue_due_runs(ctx)
    assert n == 1
    runs = list(await db_session.scalars(select(Run).where(Run.job_profile_id == p.id)))
    assert len(runs) == 1
    assert runs[0].trigger == RunTrigger.scheduled
    assert runs[0].idempotency_key.startswith(f"sched:{p.id}:")


async def test_concurrent_invocations_still_make_one_run(
    db_session, shared_sessionmaker, redis_client, make_user
):
    p = await _due_profile(db_session, make_user)
    enqueued: list[tuple] = []

    async def _enqueue(fn, *args):
        enqueued.append((fn, *args))

    ctx = {"sessionmaker": shared_sessionmaker, "redis": redis_client, "enqueue": _enqueue}

    await asyncio.gather(*(enqueue_due_runs(ctx) for _ in range(3)))
    total = await db_session.scalar(
        select(func.count()).select_from(Run).where(Run.job_profile_id == p.id)
    )
    assert total == 1


async def test_not_due_profile_is_skipped(db_session, shared_sessionmaker, redis_client, make_user):
    # a cron that won't match this minute
    now = datetime.now(UTC)
    never_min = (now.minute + 30) % 60
    await _due_profile(db_session, make_user, cron=f"{never_min} 3 1 1 *")
    enqueued: list[tuple] = []

    async def _enqueue(fn, *args):
        enqueued.append((fn, *args))

    ctx = {"sessionmaker": shared_sessionmaker, "redis": redis_client, "enqueue": _enqueue}
    assert await enqueue_due_runs(ctx) == 0
