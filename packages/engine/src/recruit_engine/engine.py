"""
run_engine — one tenant's job hunt, end to end.

Pure: it sequences scrape → dedupe → match → report against the injected ports
and emits ``on_step`` progress. No database, no environment, no scheduling, no
email transport — the worker owns those.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from .dedupe import compute_external_hash
from .matching import batch_match
from .ports import Clock, LLMClient, RateLimiter, SeenStore
from .report import build_report
from .scrapers import SCRAPERS
from .types import EngineInput, EngineResult, MatchedJob

logger = logging.getLogger(__name__)

OnStep = Callable[[str, str, dict], Awaitable[None]]

_BIG3 = "jobspy"


async def run_engine(
    inp: EngineInput,
    *,
    seen: SeenStore,
    rate_limiter: RateLimiter,
    llm: LLMClient,
    clock: Clock,
    on_step: OnStep | None = None,
) -> EngineResult:
    async def step(name: str, status: str, detail: dict | None = None) -> None:
        if on_step is not None:
            await on_step(name, status, detail or {})

    result = EngineResult(run_id=inp.run_id)
    cred_by_site = {c.site: c for c in inp.credentials}

    # ── scrape ───────────────────────────────────────────────────────────
    all_jobs = []
    for name in inp.enabled_sources:
        fetch = SCRAPERS.get(name)
        if fetch is None:
            result.per_source[name] = _src("unknown", error="no such source")
            continue
        if name == _BIG3 and not inp.profile.big3_optin:
            result.per_source[name] = _src("skipped", error="not opted in")
            await step(f"scrape:{name}", "skipped", {"reason": "big3 not opted in"})
            continue

        await step(f"scrape:{name}", "running")
        t0 = time.perf_counter()
        try:
            await rate_limiter.acquire(f"{name}:{inp.tenant_id}")
            jobs = await fetch(
                inp.profile,
                cred_by_site.get(name),
                rate_limiter,
                timeout_s=inp.limits.per_source_timeout_s,
            )
            for j in jobs:
                if not j.external_hash:
                    j.external_hash = compute_external_hash(j)
            all_jobs.extend(jobs)
            result.per_source[name] = _src("ok", found=len(jobs), latency_ms=_ms(t0))
            await step(f"scrape:{name}", "succeeded", {"found": len(jobs)})
        except Exception as exc:  # noqa: BLE001 — one bad source must not kill the run
            logger.warning("scrape:%s failed: %s", name, exc)
            result.per_source[name] = _src("failed", latency_ms=_ms(t0), error=str(exc)[:500])
            await step(f"scrape:{name}", "failed", {"error": str(exc)[:500]})

    result.scraped = len(all_jobs)

    # ── dedupe ───────────────────────────────────────────────────────────
    await step("dedupe", "running")
    hashes = [j.external_hash for j in all_jobs]
    unseen = seen.filter_new(inp.tenant_id, hashes)
    seen_now: set[str] = set()
    new_jobs = []
    for j in all_jobs:
        if j.external_hash in unseen and j.external_hash not in seen_now:
            seen_now.add(j.external_hash)
            new_jobs.append(j)
    result.new = len(new_jobs)
    await step("dedupe", "succeeded", {"new": result.new})

    # ── match ────────────────────────────────────────────────────────────
    await step("match", "running")
    matched: list[MatchedJob] = []
    if new_jobs and inp.resumes:
        scored, tally, degraded = await batch_match(
            new_jobs,
            inp.resumes,
            llm,
            batch_size=inp.limits.match_batch_size,
            max_concurrency=inp.limits.llm_max_concurrency,
        )
        result.missing_skills_tally = tally
        result.ai_degraded = degraded

        wl = {c.lower() for c in inp.profile.watchlist_companies}
        threshold = inp.profile.min_match_percent
        for m in scored:
            if m.match_percentage >= threshold or m.job.company.lower() in wl:
                matched.append(m)
    result.matched = matched
    await step("match", "succeeded", {"matched": len(matched), "degraded": result.ai_degraded})

    # ── report ───────────────────────────────────────────────────────────
    await step("report", "running")
    if matched:
        result.report_bytes = build_report(
            [_report_row(m) for m in matched],
            inp.profile.watchlist_companies,
            inp.profile.profile_id,
            tips=[],
        )
    await step("report", "succeeded", {"bytes": len(result.report_bytes or b"")})

    return result


# ── helpers ─────────────────────────────────────────────────────────────


def _ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _src(status: str, *, found: int = 0, latency_ms: int = 0, error: str | None = None) -> dict:
    return {"status": status, "found": found, "latency_ms": latency_ms, "error": error}


def _report_row(m: MatchedJob) -> dict:
    j = m.job
    return {
        "company": j.company,
        "title": j.title,
        "match_percentage": m.match_percentage,
        "matched_profile": m.matched_profile_id,
        "urgency": m.urgency,
        "apply_url": j.url,
        "location": j.location,
        "salary": j.salary or "",
        "company_type": "",
        "company_size": "",
        "matched_skills": m.matched_skills,
        "missing_skills": m.missing_skills,
        "why_good_fit": m.why_fit,
        "posted_date": j.posted_date or "",
        "source": j.source,
    }
