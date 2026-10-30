.PHONY: setup db db-down api web test lint typecheck check

setup:  ## Install all dependencies and git hooks
	uv sync
	cd web && pnpm install
	uv run pre-commit install

db:  ## Start local Postgres (pgvector) in Docker
	docker compose up -d --wait db

db-down:
	docker compose down

api:  ## Run the FastAPI dev server on :8000
	uv run uvicorn api.main:app --reload

web:  ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd web && pnpm dev

test:
	uv run pytest
	cd web && pnpm test

lint:
	uv run ruff check .
	uv run ruff format --check .
	cd web && pnpm lint

typecheck:
	uv run mypy
	cd web && pnpm typecheck

check: lint typecheck test  ## Everything CI runs
