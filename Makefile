# Recruit-ME developer entrypoints.
# Windows: install `make` (choco install make / scoop install make) or run the
# underlying commands directly — each recipe is a single line.

.PHONY: help up down logs sync test lint fmt typecheck

help:
	@echo "up        - start local infra (postgres, redis, minio)"
	@echo "down      - stop local infra"
	@echo "logs      - tail infra logs"
	@echo "sync      - resolve + install the uv workspace"
	@echo "test      - run the pytest suite"
	@echo "lint      - ruff check"
	@echo "fmt       - ruff format"
	@echo "typecheck - mypy"

up:
	docker compose up -d postgres redis minio minio-setup

down:
	docker compose down

logs:
	docker compose logs -f postgres redis minio

sync:
	uv sync --all-packages

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

typecheck:
	uv run mypy packages/engine/src
