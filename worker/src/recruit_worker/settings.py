"""arq entrypoints.

Two processes, one image, **two separate queues**:

* ``arq recruit_worker.settings.WorkerSettings``    — consumes ``JOBS_QUEUE``.
* ``arq recruit_worker.settings.SchedulerSettings`` — consumes ``CRON_QUEUE``;
  its only job is the once-a-minute ``enqueue_due_runs`` cron, which enqueues
  the real work onto ``JOBS_QUEUE``.

The queues must be distinct: a process that claims a job whose function it does
not register makes arq drop the job with no re-enqueue, so a shared queue would
silently lose scheduled runs (scheduler claims ``execute_run``) or cron fires
(a pool worker claims ``enqueue_due_runs``). ``enqueue_due_runs`` is still
idempotent — a per-profile Redis lock plus the ``sched:<id>:<date>`` key — so an
accidental second scheduler cannot double-book a run.
"""

from __future__ import annotations

import os
import socket

from arq import cron
from arq.connections import RedisSettings
from recruit_api.config import get_settings
from recruit_api.queue import CRON_QUEUE, JOBS_QUEUE

from .adapters.rate_limiter_redis import RedisTokenBucket
from .ports.llm_openrouter import OpenRouterLLM
from .scheduler import (
    deliver_pending_reports,
    enqueue_due_runs,
    requeue_stale_queued_runs,
)
from .tasks.execute_run import execute_run
from .tasks.parse_resume import parse_resume
from .tasks.verify_credential import verify_credential


async def on_startup(ctx: dict) -> None:
    from recruit_api.db import get_sessionmaker
    from recruit_api.security.crypto import build_envelope
    from recruit_api.services.email_service import build_email_sender
    from recruit_api.services.object_store import build_object_store

    s = get_settings()
    # Route all outbound scraping through the egress proxy, if configured.
    # requests and httpx both honour these.
    if s.http_proxy_url:
        os.environ.setdefault("HTTP_PROXY", s.http_proxy_url)
        os.environ.setdefault("HTTPS_PROXY", s.http_proxy_url)
    ctx["settings"] = s
    ctx["sessionmaker"] = get_sessionmaker()
    ctx["object_store"] = build_object_store(s)
    ctx["email_sender"] = build_email_sender(s)
    ctx["envelope"] = build_envelope(s)
    ctx["llm"] = OpenRouterLLM(s.openrouter_api_key, s.openrouter_model)
    ctx["llm_model"] = s.openrouter_model
    ctx["rate_limiter"] = RedisTokenBucket(ctx["redis"])
    ctx["worker_id"] = socket.gethostname()

    async def _enqueue(fn: str, *args: object) -> None:
        # Always onto the pool queue, whichever process is enqueuing.
        await ctx["redis"].enqueue_job(fn, *args, _queue_name=JOBS_QUEUE)

    ctx["enqueue"] = _enqueue


_redis_settings = RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    queue_name = JOBS_QUEUE
    functions = [parse_resume, execute_run, verify_credential]
    on_startup = on_startup
    redis_settings = _redis_settings
    max_jobs = 10
    job_timeout = 600


class SchedulerSettings:
    queue_name = CRON_QUEUE
    functions: list = []
    cron_jobs = [
        cron(enqueue_due_runs, second=0, run_at_startup=False, unique=True),
        cron(deliver_pending_reports, minute=set(range(0, 60, 5)), second=15, unique=True),
        cron(requeue_stale_queued_runs, minute=set(range(0, 60, 5)), second=30, unique=True),
    ]
    on_startup = on_startup
    redis_settings = _redis_settings
    max_jobs = 1
