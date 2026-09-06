# Recruit-ME developer entrypoints.
# Windows: install `make` (choco install make / scoop install make) or run the
# underlying command from each recipe directly — every recipe is a single line.

.PHONY: help up down logs infra migrate seed build sync test lint fmt typecheck

help:
	@echo "up        - build + start the full stack (postgres, redis, minio, api, worker, scheduler, web)"
	@echo "down      - stop the stack (keeps volumes)"
	@echo "logs      - tail all service logs"
	@echo "infra     - start only postgres, redis, minio"
	@echo "migrate   - run alembic migrations to head (one-shot container)"
	@echo "seed      - load the demo tenant + profile + runs + matches"
	@echo "build     - (re)build all images"
	@echo "sync      - resolve + install the uv workspace"
	@echo "test      - run the pytest suite"
	@echo "lint      - ruff check"
	@echo "fmt       - ruff format"
	@echo "typecheck - mypy (engine + backend + worker)"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

infra:
	docker compose up -d postgres redis minio minio-setup

migrate:
	docker compose run --rm migrate

seed:
	docker compose run --rm seed

build:
	docker compose build

sync:
	uv sync --all-packages

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy backend/src worker/src packages/engine/src
