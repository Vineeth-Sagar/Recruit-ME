"""Redis token-bucket rate limiter (``RateLimiter`` port).

``acquire("<site>:<tenant>")`` consumes one token from *both* the
per-``(site, tenant)`` bucket and the per-``site`` global bucket, atomically via
a Lua script, blocking (sleeping) until both have capacity. Buckets refill
continuously at ``rpm/60`` tokens/sec up to ``burst``.
"""

from __future__ import annotations

import asyncio
import time

from redis.asyncio import Redis

from ..policies import DEFAULT_POLICY, SitePolicy, policy_for

_LUA = """
local function level(key, rate, burst, now)
  local d = redis.call('HMGET', key, 't', 's')
  local tok = tonumber(d[1])
  local ts = tonumber(d[2])
  if tok == nil then tok = burst; ts = now end
  local elapsed = math.max(0, now - ts) / 1000.0
  return math.min(burst, tok + elapsed * rate), ts
end

local now = tonumber(ARGV[5])
local t_rate = tonumber(ARGV[1]); local t_burst = tonumber(ARGV[2])
local g_rate = tonumber(ARGV[3]); local g_burst = tonumber(ARGV[4])
local t_tok = level(KEYS[1], t_rate, t_burst, now)
local g_tok = level(KEYS[2], g_rate, g_burst, now)

if t_tok >= 1 and g_tok >= 1 then
  redis.call('HSET', KEYS[1], 't', t_tok - 1, 's', now)
  redis.call('HSET', KEYS[2], 't', g_tok - 1, 's', now)
  redis.call('PEXPIRE', KEYS[1], 300000)
  redis.call('PEXPIRE', KEYS[2], 300000)
  return {1, 0}
end

local tw = 0
local gw = 0
if t_tok < 1 then tw = math.ceil((1 - t_tok) / t_rate * 1000) end
if g_tok < 1 then gw = math.ceil((1 - g_tok) / g_rate * 1000) end
return {0, math.max(tw, gw)}
"""


class RedisTokenBucket:
    def __init__(
        self,
        redis: Redis,
        *,
        policy_lookup=policy_for,
        max_wait_s: float = 30.0,
        sleep_cap_s: float = 5.0,
    ):
        self._redis = redis
        self._policy_lookup = policy_lookup
        self._script = redis.register_script(_LUA)
        self._max_wait_s = max_wait_s
        self._sleep_cap_s = sleep_cap_s

    async def acquire(self, key: str) -> None:
        site = key.split(":", 1)[0]
        p: SitePolicy = self._policy_lookup(site) or DEFAULT_POLICY
        t_rate = p.rpm / 60.0
        g_rate = p.global_rpm / 60.0
        tenant_key = f"rl:{{{site}}}:{key}"
        global_key = f"rl:{{{site}}}:__all__"

        waited = 0.0
        while True:
            allowed, wait_ms = await self._script(
                keys=[tenant_key, global_key],
                args=[t_rate, p.burst, g_rate, p.global_burst, int(time.time() * 1000)],
            )
            if int(allowed) == 1:
                if p.min_delay_ms:
                    await asyncio.sleep(p.min_delay_ms / 1000.0)
                return
            nap = min(max(int(wait_ms), 1) / 1000.0, self._sleep_cap_s)
            waited += nap
            if waited > self._max_wait_s:
                # Don't wedge a run forever — proceed and let the site push back.
                return
            await asyncio.sleep(nap)
