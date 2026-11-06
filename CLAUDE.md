# RedwoodSearch

AI assistant for Stanford ExploreCourses: students describe the quarter they want in plain English and get a
conflict-free schedule built from real catalog data.

## Architecture

- `web/` — React + TypeScript (Vite, Tailwind). Dev server proxies `/api` to the FastAPI server on :8000.
- `api/` — FastAPI routes, Pydantic models, DB queries, Claude tool definitions.
- `core/` — pure Python scheduling logic (conflict checker, schedule search). No I/O, no LLM calls.
- `ingest/` — ExploreCourses XML downloader, parser, prerequisite extractor, and database loader.
- `db/` — database settings, migration runner, and numbered SQL migrations (shared by `api/` and `ingest/`).
- `evals/` — hand-labeled NL query → expected filter set.
- Database: Postgres + pgvector via `docker compose`, on host port **5433** (5432 is taken by a local
  Postgres.app). Tests use a separate `redwood_test` database that they wipe.

Schema changes go in a new `db/migrations/NNNN_name.sql` file; never edit an applied migration.
Prerequisites: only hard requirements count — `recommended` means "no prerequisites" for filtering.
Catalog data is refreshed manually (no nightly job); derived fields are recomputed only when a
description changes.

## Rules that must not be broken

- **The LLM never decides schedule validity.** Conflicts and unit totals come from `core/` only.
- **The LLM never states course facts.** Claude emits tool calls; the backend runs them against the DB.
  Course IDs in replies that aren't in the DB are stripped server-side. UI renders course data from DB rows.
- **SQL is always parameterized.** Never build a query string from LLM output or user text.
- Claude may only call tools on the explicit whitelist registered in `api/`.
- Secrets live only in `.env` (gitignored). Never paste keys into code, prompts, or fixtures.
- Tests use the frozen fixture snapshot, never the live ExploreCourses site.

## Edit with review only

Do not change these without flagging it to the human first: `core/`, `.github/workflows/`,
`.pre-commit-config.yaml`.

## Commands

```sh
make setup      # uv sync, pnpm install, install git hooks
make db         # start Postgres (needs Docker running); required for `make check`
make migrate    # apply pending schema migrations
make seed       # load the test snapshot into the local DB (seed-full: the whole downloaded catalog)
make fetch      # download this year's catalog into data/raw (gitignored, ~5 min)
make fixture    # rebuild the test snapshot in ingest/fixtures from data/raw
make api        # FastAPI on :8000
make web        # Vite on :5173
make check      # lint + typecheck + tests (what CI runs)
```

Single checks: `uv run pytest`, `uv run ruff check .`, `uv run mypy`, `cd web && pnpm test|lint|typecheck`.
