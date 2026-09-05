"""arq worker entrypoint:  arq recruit_worker.settings.WorkerSettings"""

from __future__ import annotations

from arq.connections import RedisSettings
from recruit_api.config import get_settings

from .ports.llm_openrouter import OpenRouterLLM
from .tasks.parse_resume import parse_resume


async def on_startup(ctx: dict) -> None:
    from recruit_api.db import get_sessionmaker
    from recruit_api.services.object_store import build_object_store

    s = get_settings()
    ctx["sessionmaker"] = get_sessionmaker()
    ctx["object_store"] = build_object_store(s)
    ctx["llm"] = OpenRouterLLM(s.openrouter_api_key, s.openrouter_model)
    ctx["llm_model"] = s.openrouter_model


class WorkerSettings:
    functions = [parse_resume]
    on_startup = on_startup
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    max_jobs = 10
    job_timeout = 120
