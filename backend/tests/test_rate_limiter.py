"""RedisTokenBucket — real Redis, bucket timing, per-tenant + global ceiling."""

from __future__ import annotations

import asyncio
import time

import pytest
from recruit_worker.adapters.rate_limiter_redis import RedisTokenBucket
from recruit_worker.policies import SitePolicy

pytestmark = pytest.mark.asyncio


def _lookup(policy: SitePolicy):
    return lambda site: policy


async def test_burst_then_throttled_to_rate(redis_client):
    # 60 rpm = 1/sec, burst 3, generous global ceiling
    p = SitePolicy(rpm=60, burst=3, global_rpm=600, global_burst=100)
    rl = RedisTokenBucket(redis_client, policy_lookup=_lookup(p), sleep_cap_s=0.3)

    start = time.perf_counter()
    for _ in range(6):
        await rl.acquire("yc:tenantA")
    elapsed = time.perf_counter() - start
    # 3 free from burst, then 3 more at ~1/sec -> at least ~2.5s
    assert elapsed >= 2.3


async def test_second_tenant_not_starved_by_first(redis_client):
    p = SitePolicy(rpm=60, burst=2, global_rpm=600, global_burst=100)
    rl = RedisTokenBucket(redis_client, policy_lookup=_lookup(p), sleep_cap_s=0.2)

    await rl.acquire("yc:tenantA")
    await rl.acquire("yc:tenantA")  # tenantA burst spent
    start = time.perf_counter()
    await rl.acquire("yc:tenantB")  # tenantB has its own bucket -> instant
    assert time.perf_counter() - start < 0.5


async def test_global_ceiling_caps_combined_throughput(redis_client):
    # per-tenant is roomy, but the site-wide bucket only has 2 tokens then 0.2/s
    p = SitePolicy(rpm=600, burst=50, global_rpm=12, global_burst=2)
    rl = RedisTokenBucket(redis_client, policy_lookup=_lookup(p), sleep_cap_s=0.5)

    start = time.perf_counter()
    await asyncio.gather(
        rl.acquire("yc:tenantA"),
        rl.acquire("yc:tenantB"),
        rl.acquire("yc:tenantC"),
        rl.acquire("yc:tenantD"),
    )
    elapsed = time.perf_counter() - start
    # 2 from global burst, then 2 more at 12/min = 5s each -> ~5s+ total
    assert elapsed >= 4.0
