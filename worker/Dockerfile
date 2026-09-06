# syntax=docker/dockerfile:1
# Recruit-ME worker image — runs the arq consumer and (with a different command)
# the scheduler. Build context is the repo root:
#   docker build -f worker/Dockerfile -t recruit-me-worker .

# ── build ──────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS build

RUN pip install --no-cache-dir "uv>=0.5,<0.6"
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY backend ./backend
COPY worker ./worker

# recruit-worker pulls in recruit-api + recruit-engine as workspace deps.
RUN uv sync --frozen --no-dev --package recruit-worker

# ── runtime ────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=build --chown=app:app /app /app

USER app

# Default: the job consumer. The scheduler service overrides this with
# `arq recruit_worker.settings.SchedulerSettings`.
CMD ["arq", "recruit_worker.settings.WorkerSettings"]
