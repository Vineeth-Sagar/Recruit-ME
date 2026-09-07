"""Regression tests for issues found in the 2026-09-07 code audit."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.asyncio


async def test_scheduler_and_worker_use_separate_queues():
    """Q1: a shared queue silently drops jobs whose function the winning
    process doesn't register."""
    from recruit_worker.settings import SchedulerSettings, WorkerSettings

    assert WorkerSettings.queue_name != SchedulerSettings.queue_name
    assert WorkerSettings.queue_name and SchedulerSettings.queue_name


async def test_enqueue_targets_the_jobs_queue(monkeypatch):
    """Q1: every explicit enqueue must land on the pool queue."""
    from recruit_api import queue

    captured = {}

    class _FakePool:
        async def enqueue_job(self, fn, *args, **kw):
            captured["fn"] = fn
            captured["queue"] = kw.get("_queue_name")

    monkeypatch.setattr(queue, "_get_pool", lambda: _fake_pool())

    async def _fake_pool():
        return _FakePool()

    await queue.enqueue("execute_run", "abc")
    assert captured["fn"] == "execute_run"
    assert captured["queue"] == queue.JOBS_QUEUE


async def test_match_percentage_coercion_never_raises():
    """W8: the LLM can return '85%', 'high', 120, None — none may crash."""
    from recruit_engine.matching import _as_pct, _as_str_list

    assert _as_pct("85%") == 85
    assert _as_pct("high") == 0
    assert _as_pct(120) == 100
    assert _as_pct(-5) == 0
    assert _as_pct(None) == 0
    assert _as_pct(True) == 0
    assert _as_str_list("Kafka") == ["Kafka"]
    assert _as_str_list(["a", "", "b"]) == ["a", "b"]
    assert _as_str_list(None) == []


async def test_external_hash_is_source_independent():
    """W6: jobspy reports `source` inconsistently — same URL must be one hash."""
    from recruit_engine.dedupe import compute_external_hash
    from recruit_engine.types import JobPosting

    a = JobPosting(source="LinkedIn", company="Acme", title="SDE", url="https://acme.com/j/1")
    b = JobPosting(
        source="linkedin,indeed", company="Acme", title="SDE", url="https://acme.com/j/1"
    )
    assert compute_external_hash(a) == compute_external_hash(b)


async def test_transient_classification_covers_real_infra_errors():
    """W2: botocore / httpx 5xx outages must be retryable, not permanent."""
    import httpx
    from botocore.exceptions import EndpointConnectionError
    from recruit_worker.tasks.execute_run import _is_transient

    assert _is_transient(EndpointConnectionError(endpoint_url="http://x"))
    assert _is_transient(
        httpx.HTTPStatusError(
            "500", request=httpx.Request("GET", "http://x"), response=httpx.Response(500)
        )
    )
    assert _is_transient(RuntimeError("503 Service Unavailable"))
    assert not _is_transient(ValueError("bad input"))
