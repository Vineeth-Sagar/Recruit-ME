"""
Async adapters that give the four kept scrapers a uniform shape.

Each ``*_fetch`` takes a ``ProfileSpec`` and returns ``list[JobPosting]``. The
underlying scraper modules are still synchronous ``requests``-based code; the
adapter runs them in a worker thread with a hard timeout and normalises the
result dicts. Rate limiting is applied by the engine *before* it calls the
adapter (one token per source per run); ``rl`` is threaded through for future
per-request limiting.
"""

from __future__ import annotations

import asyncio

from ..ports import RateLimiter
from ..types import JobPosting, ProfileSpec, SourceCredential
from .hn_scraper import scrape_hn_hiring
from .jobspy_scraper import scrape_jobspy
from .wellfound_scraper import scrape_wellfound
from .yc_scraper import scrape_yc_jobs


async def _run_sync(fn, *args, timeout_s: int):
    return await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout=timeout_s)


def _norm(d: dict, fallback_source: str) -> JobPosting:
    return JobPosting(
        source=str(d.get("source") or fallback_source),
        company=str(d.get("company", "")),
        title=str(d.get("title", "")),
        location=str(d.get("location", "")),
        description=str(d.get("description", "")),
        url=str(d.get("apply_url") or d.get("url") or ""),
        posted_date=str(d.get("posted_date")) or None,
        salary=str(d.get("salary")) or None,
    )


async def jobspy_fetch(
    spec: ProfileSpec, cred: SourceCredential | None, rl: RateLimiter, *, timeout_s: int
) -> list[JobPosting]:
    enabled = {"linkedin": True, "indeed": True, "glassdoor": True}
    dicts = await _run_sync(
        scrape_jobspy, spec.target_roles, spec.locations, enabled, timeout_s=timeout_s
    )
    return [_norm(d, "LinkedIn/Indeed/Glassdoor") for d in dicts]


async def wellfound_fetch(
    spec: ProfileSpec, cred: SourceCredential | None, rl: RateLimiter, *, timeout_s: int
) -> list[JobPosting]:
    dicts = await _run_sync(scrape_wellfound, spec.target_roles, timeout_s=timeout_s)
    return [_norm(d, "Wellfound") for d in dicts]


async def yc_fetch(
    spec: ProfileSpec, cred: SourceCredential | None, rl: RateLimiter, *, timeout_s: int
) -> list[JobPosting]:
    dicts = await _run_sync(scrape_yc_jobs, spec.target_roles, spec.locations, timeout_s=timeout_s)
    return [_norm(d, "YC Jobs") for d in dicts]


async def hackernews_fetch(
    spec: ProfileSpec, cred: SourceCredential | None, rl: RateLimiter, *, timeout_s: int
) -> list[JobPosting]:
    dicts = await _run_sync(
        scrape_hn_hiring, spec.target_roles, spec.locations, timeout_s=timeout_s
    )
    return [_norm(d, "HackerNews") for d in dicts]


SCRAPERS = {
    "jobspy": jobspy_fetch,
    "wellfound": wellfound_fetch,
    "yc": yc_fetch,
    "hackernews": hackernews_fetch,
}
