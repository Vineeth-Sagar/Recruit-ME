# Deploying Recruit-ME

Two topologies: a one-host `docker compose` stack (dev, demos, small self-hosts)
and a Kubernetes layout for anything that needs to scale. Both run **the same
three images** — `api`, `worker`, `web` — built from `backend/Dockerfile`,
`worker/Dockerfile`, `frontend/Dockerfile`.

---

## 1. Local / single host — docker compose

```bash
git clone https://github.com/Vineeth-Sagar/Recruit-ME && cd Recruit-ME
cp .env.example .env            # defaults are dev-safe; edit for anything real
make up                         # build + start; runs the migrate job on the way
make seed                       # demo@recruit.me / demo-password-123
open http://localhost:3000
```

Services and host ports:

| service     | image              | port          | notes                                             |
|-------------|--------------------|---------------|---------------------------------------------------|
| `postgres`  | postgres:16-alpine | 15432         | volume `pgdata`; `infra/postgres/init.sql` on init |
| `redis`     | redis:7-alpine     | 16379         | queue, rate-limit buckets, scheduler locks        |
| `minio`     | minio              | 19000 / 19001 | volume `miniodata`; `minio-setup` makes the bucket |
| `migrate`   | recruit-me-api     | –             | one-shot `alembic upgrade head`, then exits       |
| `api`       | recruit-me-api     | 8000          | `/health`; waits on `migrate` + `minio-setup`     |
| `worker`    | recruit-me-worker  | –             | `arq …WorkerSettings` — drains the job queue      |
| `scheduler` | recruit-me-worker  | –             | `arq …SchedulerSettings` — cron only, 1 replica   |
| `web`       | recruit-me-web     | 3000          | Next standalone; proxies `/api/*` → `api:8000`    |
| `seed`      | recruit-me-api     | –             | `profiles: [tools]`; run via `make seed`          |

`make down` stops the stack and keeps volumes. `docker compose down -v` wipes
Postgres and MinIO for a clean slate.

**Hot reload:** `cp docker-compose.override.yml.example docker-compose.override.yml`
then `docker compose up` — source is bind-mounted and each service runs its
reloading entrypoint.

**Email locally:** `EMAIL_PROVIDER=console` writes each message to
`docker compose logs api` / `logs worker`. Set `EMAIL_PROVIDER=resend` +
`RESEND_API_KEY` for real delivery.

**The `/api` proxy:** in the compose stack the browser calls `/api/*` on the web
origin and the Next server proxies to the API. That target is baked at image
build time from `--build-arg API_PROXY_TARGET` (default `http://api:8000`) — the
standalone server does not re-read it at runtime. Behind a real reverse proxy or
a k8s Ingress that already routes `/api` to the API service, those calls never
reach the Next server, so the baked value is irrelevant there.

---

## 2. Kubernetes (architected, not shipped)

```
                 ┌─────────── Ingress (TLS) ───────────┐
                 │  /api/*  → api Service              │
                 │  /*      → web Service              │
                 └────────────────────────────────────┘
   api Deployment ×N (stateless, HPA on CPU/RPS)
   worker Deployment  — KEDA ScaledObject on Redis list length, split into
                        `scrape` and `match` pools (separate arq queues)
   scheduler Deployment ×1  — leaderElection so only one cron fires
   web Deployment ×N (stateless)
   migrate Job  — runs once per release, before the api rollout
   managed Postgres · managed Redis · S3 (or MinIO Operator)
   secrets from the platform secret manager, mounted as env
   egress for the worker pools via a NAT gateway / proxy pool
```

### Each compose service → a Deployment

| compose      | k8s object       | replicas | key settings |
|--------------|------------------|----------|--------------|
| `api`        | Deployment + HPA | 2–N      | `readinessProbe: GET /health`; `ENV=prod` |
| `worker`     | Deployment + KEDA | 0–N     | one Deployment per pool; `--queue-name scrape|match` |
| `scheduler`  | Deployment       | 1        | `leaderElection` (or a single replica + PDB `maxUnavailable: 0`) |
| `web`        | Deployment + HPA | 2–N      | built with `--build-arg API_PROXY_TARGET=http://api:8000` (baked, not runtime) |
| `migrate`    | Job              | 1        | `helm.sh/hook: pre-install,pre-upgrade` |

### Worker autoscale trigger — Redis list length

arq stores queued jobs in a Redis list per queue. Scale on its length:

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: recruit-worker-scrape
spec:
  scaleTargetRef:
    name: recruit-worker-scrape
  minReplicaCount: 0
  maxReplicaCount: 20
  cooldownPeriod: 120
  triggers:
    - type: redis
      metadata:
        address: redis:6379
        listName: arq:queue:scrape      # arq queue key
        listLength: "20"                 # target jobs per replica
```

The `match` pool gets its own `ScaledObject` on `arq:queue:match`. Splitting the
queues keeps a burst of slow LLM matching from starving fast scrape jobs.

### Production checklist

- `ENV=prod`, real `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`, real
  `CREDENTIAL_MASTER_KEY` (see `.env.example` for generators). The app refuses to
  start in prod without the credential key.
- Managed Postgres with `citext` + `pgcrypto` enabled by an admin
  (`infra/postgres/init.sql`), automated backups, PITR.
- Managed Redis with persistence for the queue; a separate logical DB or instance
  for rate-limit buckets is optional.
- S3 bucket with lifecycle rules on `reports/` (expire) and versioning on
  `resumes/`. The app never makes objects public.
- Worker egress through a NAT gateway or proxy pool; set `HTTP_PROXY_URL`.
  Keep `BIG3_ENABLED_GLOBAL=false` unless you accept the ToS risk in the README.
- Observability: OpenTelemetry traces from `api` + `worker`, Sentry for errors,
  and dashboards on queue depth and per-source success rate.
- `images.yml` builds and Trivy-scans all three images on a `v*` tag and pushes
  to GHCR; deployments pin an immutable `@sha256:` digest.

See `RUNBOOK.md` for day-2 operations.
