"""enqueue_due_runs — arq cron, once a minute. Enqueues one run per active
profile whose cron is due this minute, guarded by a per-profile Redis lock and
the ``runs.idempotency_key`` unique constraint."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo

from croniter import croniter
from recruit_api.models.job_profile import JobProfile
from recruit_api.models.run import Run, RunStatus, RunTrigger
from sqlalchemy import select

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

    return enqueued
