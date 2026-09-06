# Recruit-ME

An open-source, multi-tenant job-search automation platform. Any user signs up,
builds a job profile (target roles, locations, filters, résumé), and the platform
runs isolated background jobs that scrape job boards, score every posting against
their résumé with an LLM, and deliver a ranked report.

It is a rebuild of the single-user automation
[EZ-Recruit](https://github.com/Vineeth-Sagar/EZ-Recruit) — same core matching
engine, re-architected so one engine serves every tenant and all per-user
variation is data.

> **Scope:** discovery, matching, and alerting. The platform does **not** log into
> job sites as the user or submit applications on their behalf.

## Status

All seven build phases are implemented. The stack runs end to end from a fresh
clone.

- Design doc: [`docs/architecture.html`](docs/architecture.html) — analysis of the
  original automation, the target architecture (diagrams + data model + execution
  model), the terms-of-service decisions, and the 7-phase build plan with file
  paths, key signatures, and per-phase verification.
- Operations: [`docs/DEPLOY.md`](docs/DEPLOY.md) (compose + Kubernetes topology),
  [`docs/RUNBOOK.md`](docs/RUNBOOK.md) (day-2).

## Quickstart

```bash
cp .env.example .env          # dev-safe defaults; edit for anything real
make up                       # build + start postgres, redis, minio, api, worker, scheduler, web
make seed                     # demo tenant: demo@recruit.me / demo-password-123
open http://localhost:3000
```

`make down` stops the stack (keeps data); `docker compose down -v` wipes it.
For hot-reload development, `cp docker-compose.override.yml.example docker-compose.override.yml`
first. Without Docker, `make infra` brings up just Postgres/Redis/MinIO and the
services run from the uv workspace (`uv sync`, then `uv run …`).

## Planned architecture

| Layer | Choice |
| :--- | :--- |
| Frontend | Next.js 14 (App Router) + shadcn/ui |
| API | FastAPI — reads, writes, and **enqueues** only; never runs automation inline |
| Workers | Arq on Redis; stateless pool running `packages/engine` per tenant |
| Engine | `packages/engine` — pure library, no DB / auth / network config |
| Relational store | PostgreSQL (row-level multi-tenancy) |
| Queue / cache / rate limits | Redis (queue, per-`(site,user)` token buckets, locks) |
| Object storage | S3-compatible (résumés, generated reports) |
| Auth | JWT access + rotating refresh tokens, RBAC scaffold |
| Email | Transactional provider (Resend by default, behind an interface) |
| Local dev | Docker Compose |

## Build phases

1. **Repo restructuring** — uv workspace: `packages/engine`, `backend`, `worker`; standalone `frontend`
2. **Auth + user accounts** — argon2id, JWT + rotating refresh, RBAC, email verification
3. **Job-profile builder + persistence** — profiles, résumés, object storage, async parse
4. **Tenant-aware queued engine** — `run_engine()`, `execute_run` task, rate limiter, idempotency, scheduler
5. **Dashboard** — run history, live progress (SSE), matches table, metrics
6. **Account settings + encrypted credentials** — `site_credentials` with envelope encryption, consent screens
7. **Deployment config** — Docker Compose, env templates, seed data, CI, production topology notes

Each phase merges only when its verification checklist passes.

## Job sources

**Included:** LinkedIn / Indeed / Glassdoor (via `python-jobspy`, behind a per-profile
opt-in flag that is off by default), Wellfound, Y Combinator, Hacker News "Who is
Hiring?". **Optional:** SerpAPI (user supplies their own key).

**Not included:** Naukri, Unstop, Internshala, Cutshort — these relied on
undocumented endpoints or HTML scraping and are dropped for a public service.

## License

[AGPL-3.0](LICENSE) — a modified version run as a network service must publish its
source.
