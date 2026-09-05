# recruit-api

FastAPI backend. It reads, writes, and **enqueues** — automation never runs
inside a request.

## Phase 4.2 — auth + accounts

- `config.py` — `Settings` from env / `.env`
- `db.py` — async SQLAlchemy engine + `get_db` session dependency
- `models/` — `User` (+ role/plan/status), `RefreshToken`, `EmailVerificationToken`, `PasswordResetToken`
- `security/` — argon2id passwords, RS256 access tokens, `get_current_user` / `require_role` / `require_plan`
- `services/auth_service.py` — signup, login, **rotating** refresh with reuse detection, email verify, password reset
- `services/email_service.py` — `EmailSender` protocol; console sender (dev) + Resend sender
- `routers/` — `/api/v1/auth/*`, `/api/v1/me`, `/api/v1/admin/*`
- `migrations/` — Alembic (async); `0001_users_auth`

## Run

```bash
# from the repo root, infra up (make up)
uv run alembic -c backend/alembic.ini upgrade head
uv run uvicorn recruit_api.main:app --reload --port 8000
# docs at http://localhost:8000/docs
```

## Test

```bash
uv run pytest backend
```

Tests use a throwaway Postgres: `TEST_DATABASE_URL` if set, otherwise a
`testcontainers` Postgres (needs Docker). Each test runs in a rolled-back
transaction.
