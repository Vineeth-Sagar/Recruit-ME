"""
run_engine — the single entry point.

Phase 4.1 ships the signature and the contract only. The implementation
(scrape → dedupe → match → report, sequencing the existing modules against the
injected ports and emitting ``on_step`` progress) lands in Phase 4.4. It is
derived from EZ-Recruit's ``job_hunter/main.py::run()`` — see PORTING.md.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from .ports import Clock, LLMClient, RateLimiter, SeenStore
from .types import EngineInput, EngineResult

OnStep = Callable[[str, str, dict], Awaitable[None]]
"""(step_name, status, detail) -> awaitable. e.g. ("scrape:wellfound", "running", {})."""


async def run_engine(
    inp: EngineInput,
    *,
    seen: SeenStore,
    rate_limiter: RateLimiter,
    llm: LLMClient,
    clock: Clock,
    on_step: OnStep | None = None,
) -> EngineResult:
    """Run one tenant's job hunt end to end and return a persistable result.

    Pure: no database, no environment reads, no scheduling, no email transport.
    """
    raise NotImplementedError("run_engine is implemented in Phase 4.4")
