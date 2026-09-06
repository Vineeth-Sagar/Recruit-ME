# syntax=docker/dockerfile:1
# Recruit-ME API image. Build context is the repo root:
#   docker build -f backend/Dockerfile -t recruit-me-api .

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
COPY scripts ./scripts

# Only recruit-api and its dependency subtree (pulls in recruit-engine).
RUN uv sync --frozen --no-dev --package recruit-api

# ── runtime ────────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=build --chown=app:app /app /app

USER app
EXPOSE 8000

# Migrations are a separate one-shot service (see docker-compose.yml); this just serves.
CMD ["uvicorn", "recruit_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
