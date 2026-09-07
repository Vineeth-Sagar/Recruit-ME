"""Scheduler cron jobs (run only by the SchedulerSettings process):

- ``enqueue_due_runs``       — once a minute, enqueue one run per active profile
  whose cron is due, guarded by a per-profile Redis lock and the
  ``runs.idempotency_key`` unique constraint.
- ``deliver_pending_reports`` — sweep terminal runs that produced matches but
  whose report never went out (a persistent notify failure), and re-deliver.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

from croniter import croniter
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.run import Run, RunStatus, RunTrigger
from sqlalchemy import select

from .persistence import notify_if_needed

logger = logging.getLogger("recruit_worker.scheduler")


def _zone(tz_name: str) -> tzinfo:
    try:
        return ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def _is_due(cron_expr: str, tz_name: str, now_utc: datetime) -> bool:
    # croniter.match wants a naive datetime in the target timezone.
    local = now_utc.astimezone(_zone(tz_name)).replace(tzinfo=None, second=0, microsecond=0)
    try:
        return bool(croniter.match(cron_expr, local))
    except (ValueError, KeyError):
        logger.warning("bad cron %r on a profile — skipping", cron_expr)
        return False


def _local_date(tz_name: str, now_utc: datetime) -> str:
    return now_utc.astimezone(_zone(tz_name)).strftime("%Y-%m-%d")


async def enqueue_due_runs(ctx: dict) -> int:
    sessionmaker = ctx["sessionmaker"]
    redis = ctx["redis"]
    enqueue = ctx["enqueue"]  # (fn_name, *args) -> awaitable
    now = datetime.now(UTC)
    enqueued = 0

    async with sessionmaker() as db:
        profiles = list(
            await db.scalars(
                select(JobProfile).where(
                    JobProfile.is_active.is_(True),
                    JobProfile.schedule_cron.is_not(None),
                )
            )
        )

        for p in profiles:
            try:
                if not _is_due(p.schedule_cron, p.timezone, now):
                    continue

                idem = f"sched:{p.id}:{_local_date(p.timezone, now)}"
                lock = redis.lock(f"lock:sched:{p.id}", timeout=30)
                if not await lock.acquire(blocking=False):
                    continue
                try:
                    dupe = await db.scalar(select(Run.id).where(Run.idempotency_key == idem))
                    if dupe is not None:
                        continue
                    run = Run(
                        user_id=p.user_id,
                        job_profile_id=p.id,
                        trigger=RunTrigger.scheduled,
                        status=RunStatus.queued,
                        idempotency_key=idem,
                        queued_at=now,
                    )
                    db.add(run)
                    await db.flush()
                    await db.commit()
                    await enqueue("execute_run", str(run.id))
                    enqueued += 1
                    logger.info("scheduled run %s for profile %s", run.id, p.id)
                finally:
                    try:
                        await lock.release()
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001 — one bad profile must not skip the rest
                await db.rollback()
                logger.exception("scheduling profile %s failed", p.id)

    return enqueued


async def requeue_stale_queued_runs(ctx: dict) -> int:
    """Re-enqueue runs stuck in ``queued`` with no worker pickup — the row was
    committed but the ``enqueue`` call failed (Redis blip at creation time)."""
    sessionmaker = ctx["sessionmaker"]
    enqueue = ctx["enqueue"]
    cutoff = datetime.now(UTC) - timedelta(minutes=3)
    n = 0
    async with sessionmaker() as db:
        runs = list(
            await db.scalars(
                select(Run).where(
                    Run.status == RunStatus.queued,
                    Run.created_at < cutoff,
                    Run.started_at.is_(None),
                )
            )
        )
        for run in runs:
            await enqueue("execute_run", str(run.id))
            n += 1
            logger.info("re-enqueued stale run %s", run.id)
    return n


async def deliver_pending_reports(ctx: dict) -> int:
    """Re-send reports for finished runs that produced matches but never notified.

    Covers the residual case where ``execute_run`` exhausted its retries on the
    notification step: the run is terminal, ``notified_at`` is NULL, and matches
    exist. Bounded to the last 24h so a permanently broken run isn't retried
    forever.
    """
    sessionmaker = ctx["sessionmaker"]
    since = datetime.now(UTC) - timedelta(hours=24)
    sent = 0
    async with sessionmaker() as db:
        runs = list(
            await db.scalars(
                select(Run).where(
                    Run.status.in_([RunStatus.succeeded, RunStatus.partial]),
                    Run.notified_at.is_(None),
                    Run.finished_at.is_not(None),
                    Run.finished_at >= since,
                )
            )
        )
        for run in runs:
            try:
                if await notify_if_needed(
                    db,
                    run,
                    email_sender=ctx["email_sender"],
                    object_store=ctx["object_store"],
                ):
                    sent += 1
            except Exception:  # noqa: BLE001
                await db.rollback()
                logger.warning("pending report for run %s still undeliverable", run.id)
    if sent:
        logger.info("delivered %s pending report(s)", sent)
    return sent
