# Runbook

Day-2 operations for a running Recruit-ME deployment. Commands assume the
`docker compose` stack; the k8s equivalents are `kubectl exec` / `kubectl scale`.

## Health & smoke

```bash
curl -fsS localhost:8000/health                       # API
docker compose ps                                     # every service healthy?
docker compose run --rm api python scripts/seed.py    # reset the demo tenant
```

## A run is stuck in `running`

1. `docker compose logs --tail=200 worker` — look for the run id and a traceback.
2. The worker is idempotent: `save_result` upserts and the email is guarded by
   `runs.notified_at`. It's safe to requeue.

   ```bash
   docker compose exec redis redis-cli LLEN arq:queue
   docker compose exec api python - <<'PY'
   import asyncio
   from arq import create_pool
   from arq.connections import RedisSettings
   from recruit_api.config import get_settings

   async def main():
       pool = await create_pool(RedisSettings.from_dsn(get_settings().redis_url))
       await pool.enqueue_job("execute_run", "<RUN_ID>")

   asyncio.run(main())
   PY
   ```
3. If it will never progress, mark it terminal in the DB (`status='failed'`,
   `finished_at=now()`); the next scheduled run picks up where it left off.

## Restart the worker mid-run

`docker compose restart worker` is safe. On redelivery the task no-ops if the run
is already terminal, otherwise it resumes; exactly one notification is sent
because it is gated on `runs.notified_at` and the report is rebuilt from the DB.

## Scale the workers

- compose: `docker compose up -d --scale worker=4`
- k8s: the KEDA `ScaledObject` (see `DEPLOY.md`) handles this; to pin,
  `kubectl scale deploy/recruit-worker-scrape --replicas=4`.

Never run more than one `scheduler`. If you must restart it, a brief gap is
fine — a missed minute just means the next `enqueue_due_runs` tick schedules the
day's run (the idempotency key is `sched:<profile>:<date>`).

## Rotate the credential master key

1. Generate a new key:
   `uv run python -c "from recruit_api.security.crypto import generate_master_key_b64 as g; print(g())"`
2. Set both keys and bump the version so new writes use v2, old rows still read:
   ```
   CREDENTIAL_MASTER_KEYS=1:<old_b64>,2:<new_b64>
   CREDENTIAL_KEY_VERSION=2
   ```
3. Roll `api` + `worker` + `scheduler`.
4. Re-seal existing rows by re-saving each credential (users hit
   *Settings → Site credentials → Replace*), or run a one-off that decrypts with
   the old version and calls `Envelope.encrypt` again. Once every row is at v2,
   drop `1:<old_b64>` from `CREDENTIAL_MASTER_KEYS`.

## A job source starts failing / gets blocked

- One bad source degrades a run to `partial`; it still emails what it found.
  Check `run_sources.error` for the run.
- Persistent 403/429 on LinkedIn/Indeed/Glassdoor: those are ToS-gated and
  fragile by design. Turn the profile's `big3_optin` off, or route worker egress
  through a fresh proxy (`HTTP_PROXY_URL`) and lower the rate-limit RPM.

## Database

```bash
# backup
docker compose exec -T postgres pg_dump -U recruit recruit | gzip > backup.sql.gz
# restore into a fresh volume
zcat backup.sql.gz | docker compose exec -T postgres psql -U recruit recruit
# migrations
docker compose run --rm migrate                       # to head
docker compose run --rm api alembic -c backend/alembic.ini downgrade -1
```

## Object storage filling up

`reports/` grows one xlsx per run per tenant. Add an S3 lifecycle rule (30–90d
expiry) or, on MinIO, `mc ilm rule add --expire-days 60 local/recruit/reports/`.
`resumes/` is small and should be kept.
