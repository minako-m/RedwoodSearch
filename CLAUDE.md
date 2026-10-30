# RedwoodSearch

AI assistant for Stanford ExploreCourses: students describe the quarter they want in plain English and get a
conflict-free schedule built from real catalog data.

## Architecture

- `web/` — React + TypeScript (Vite, Tailwind). Dev server proxies `/api` to the FastAPI server on :8000.
- `api/` — FastAPI routes, Pydantic models, DB queries, Claude tool definitions.
- `core/` — pure Python scheduling logic (conflict checker, schedule search). No I/O, no LLM calls.
- `ingest/` — ExploreCourses XML parser and the job that loads the database.
- `evals/` — hand-labeled NL query → expected filter set.
- Database: Postgres + pgvector, run locally via `docker compose`.

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
make db         # start Postgres (needs Docker running)
make api        # FastAPI on :8000
make web        # Vite on :5173
make check      # lint + typecheck + tests (what CI runs)
```

Single checks: `uv run pytest`, `uv run ruff check .`, `uv run mypy`, `cd web && pnpm test|lint|typecheck`.
