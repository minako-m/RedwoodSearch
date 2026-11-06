.PHONY: setup db db-down migrate seed seed-full fetch fixture api web check check-api check-web

setup:  ## Install all dependencies and git hooks
	uv sync
	cd web && pnpm install
	uv run pre-commit install

db:  ## Start local Postgres (pgvector) in Docker
	docker compose up -d --wait db

db-down:
	docker compose down

migrate:  ## Apply pending schema migrations to the local database
	uv run python -m db.migrate

seed:  ## Load the test snapshot (~200 courses) into the local database
	uv run python -m ingest.load --source ingest/fixtures/2026-2027

seed-full:  ## Load the whole downloaded catalog (run `make fetch` first)
	uv run python -m ingest.load --source data/raw/2026-2027

fetch:  ## Download this year's offered courses from ExploreCourses into data/raw (~5 min)
	uv run python -m ingest.fetch

fixture:  ## Rebuild the ~200-course test snapshot in ingest/fixtures from data/raw
	uv run python -m ingest.make_fixture

api:  ## Run the FastAPI dev server on :8000
	uv run uvicorn api.main:app --reload

web:  ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd web && pnpm dev

# CI runs check-api and check-web; keep every check defined here and only here.
check: check-api check-web

check-api:  ## Lint, typecheck, and test the Python side
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest

check-web:  ## Lint, typecheck, and test the web side
	cd web && pnpm lint
	cd web && pnpm typecheck
	cd web && pnpm test
