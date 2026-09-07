"""execute_run — one queued Run, end to end, with idempotent re-delivery + retry.

Each DB session block is self-contained. On failure the outer wrapper opens a
fresh session to mark the run ``queued`` (transient → arq ``Retry``) or
``failed``. Every write inside is idempotent, so a retry resumes cleanly:
``save_result`` upserts, and ``notify_if_needed`` is guarded by
``runs.notified_at`` and builds its report from the DB, not this attempt's
in-memory matches. If a retry lands after the matches were already saved, the
scrape/match phase is skipped and only the notification is re-attempted.
"""

from __future__ import annotations

import asyncio
import logging
import random
import uuid
from datetime import UTC, datetime

import httpx
from arq import Retry
from botocore.exceptions import BotoCoreError
from recruit_api.models.run import Run, RunStatus
from recruit_engine.engine import run_engine

from ..adapters.seen_store_pg import PgSeenStore
from ..persistence import clear_steps, notify_if_needed, persist_step, save_result
from ..run_context import build_input

logger = logging.getLogger("recruit_worker.execute_run")

_TRANSIENT_TYPES: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    BotoCoreError,  # EndpointConnectionError, ConnectionClosedError, ...
    httpx.TransportError,  # ConnectError, ReadTimeout, RemoteProtocolError, ...
)
_TRANSIENT_HINTS = (
    "timeout",
    "429",
    "500",
    "502",
    "503",
    "504",
    "connection reset",
    "connection refused",
    "connection closed",
    "connection aborted",
    "broken pipe",
    "eof occurred",
    "temporarily unavailable",
    "service unavailable",
    "bad gateway",
    "gateway timeout",
    "server disconnected",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, _TRANSIENT_TYPES):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code >= 500 or exc.response.status_code == 429
    s = str(exc).lower()
    return any(h in s for h in _TRANSIENT_HINTS)


def _backoff_seconds(attempt: int) -> float:
    return min(2**attempt * 5, 300) + random.uniform(0, 5)


async def execute_run(ctx: dict, run_id: str) -> None:
    sessionmaker = ctx["sessionmaker"]
    try:
        await _run_once(ctx, run_id)
    except Retry:
        raise
    except (Exception, asyncio.CancelledError) as exc:  # noqa: BLE001
        # asyncio.CancelledError is how arq's job_timeout surfaces — it is a
        # BaseException, so it would otherwise slip past and leave the run stuck
        # at `running`. Treat a timeout as transient.
        transient = _is_transient(exc) or isinstance(exc, asyncio.CancelledError)
        async with sessionmaker() as db:
            run = await db.get(Run, uuid.UUID(run_id))
            if run is None:
                return
            if transient and run.attempt < run.max_attempts:
                run.status = RunStatus.queued
                run.error_summary = f"transient: {type(exc).__name__}: {exc}"[:2000]
                await db.commit()
                logger.warning("run %s transient failure, retrying: %s", run_id, exc)
                raise Retry(defer=_backoff_seconds(run.attempt)) from exc
            # Out of retries. If the run produced matches, the work succeeded and
            # only delivery is outstanding — mark it partial (not failed) and
            # leave notified_at NULL so the scheduler's sweep can still deliver.
            has_matches = bool((run.stats or {}).get("matched"))
            run.status = RunStatus.partial if has_matches else RunStatus.failed
            run.error_summary = f"{type(exc).__name__}: {exc}"[:2000]
            run.finished_at = _now()
            await db.commit()
            logger.exception("run %s -> %s", run_id, run.status)
        if isinstance(exc, asyncio.CancelledError):
            raise


async def _run_once(ctx: dict, run_id: str) -> None:
    sessionmaker = ctx["sessionmaker"]

    async with sessionmaker() as db:
        run = await db.get(Run, uuid.UUID(run_id))
        if run is None:
            logger.warning("run %s not found", run_id)
            return
        if run.is_terminal and run.notified_at is not None:
            logger.info("run %s already %s — no-op", run_id, run.status)
            return

        # Fast path: a retry after the matches were already saved. Skip the
        # scrape/match phase (re-hitting job sites) and only retry the report.
        already_scored = (run.stats or {}).get("matched") is not None
        if already_scored and run.notified_at is None:
            logger.info("run %s already scored — retrying notification only", run_id)
            run.attempt += 1
            run.worker_id = ctx.get("worker_id", "worker")
            await db.commit()
            await notify_if_needed(
                db, run, email_sender=ctx["email_sender"], object_store=ctx["object_store"]
            )
            if not run.is_terminal:
                run.status = (
                    RunStatus.partial
                    if (run.stats or {}).get("sources_failed")
                    else RunStatus.succeeded
                )
                run.finished_at = run.finished_at or _now()
                await db.commit()
            return

        run.status = RunStatus.running
        run.started_at = run.started_at or _now()
        run.attempt += 1
        run.worker_id = ctx.get("worker_id", "worker")
        run.error_summary = None
        await clear_steps(db, run.id)
        await db.commit()

        inp, known = await build_input(db, run, envelope=ctx.get("envelope"))
        seen = PgSeenStore(known)

        async def on_step(name: str, status: str, detail: dict) -> None:
            await persist_step(db, run.id, name, status, detail)
            await db.commit()

        result = await run_engine(
            inp,
            seen=seen,
            rate_limiter=ctx["rate_limiter"],
            llm=ctx["llm"],
            clock=_Clock(),
            on_step=on_step,
        )

        await save_result(db, run, result)
        await db.commit()  # matches visible even if the notify step fails

        await notify_if_needed(
            db, run, email_sender=ctx["email_sender"], object_store=ctx["object_store"]
        )

        failed_sources = any(i.get("status") == "failed" for i in result.per_source.values())
        run.status = RunStatus.partial if failed_sources else RunStatus.succeeded
        run.finished_at = _now()
        await db.commit()
        logger.info("run %s -> %s (%s matches)", run_id, run.status, len(result.matched))


class _Clock:
    def now(self) -> datetime:
        return _now()
