"""arq worker entrypoint:  arq recruit_worker.settings.WorkerSettings"""

from __future__ import annotations

import socket

from arq import cron
from arq.connections import RedisSettings
from recruit_api.config import get_settings

from .adapters.rate_limiter_redis import RedisTokenBucket
from .ports.llm_openrouter import OpenRouterLLM
from .scheduler import enqueue_due_runs
from .tasks.execute_run import execute_run
from .tasks.parse_resume import parse_resume


async def on_startup(ctx: dict) -> None:
    from recruit_api.db import get_sessionmaker
    from recruit_api.services.email_service import build_email_sender
    from recruit_api.services.object_store import build_object_store

    s = get_settings()
    ctx["settings"] = s
    ctx["sessionmaker"] = get_sessionmaker()
    ctx["object_store"] = build_object_store(s)
    ctx["email_sender"] = build_email_sender(s)
    ctx["llm"] = OpenRouterLLM(s.openrouter_api_key, s.openrouter_model)
    ctx["llm_model"] = s.openrouter_model
    ctx["rate_limiter"] = RedisTokenBucket(ctx["redis"])
    ctx["worker_id"] = socket.gethostname()

    async def _enqueue(fn: str, *args: object) -> None:
        await ctx["redis"].enqueue_job(fn, *args)

    ctx["enqueue"] = _enqueue


class WorkerSettings:
    functions = [parse_resume, execute_run]
    cron_jobs = [cron(enqueue_due_runs, second=0, run_at_startup=False)]
    on_startup = on_startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 600
