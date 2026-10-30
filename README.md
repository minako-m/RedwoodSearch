# RedwoodSearch
AI Assistant for Stanford's ExploreCourses and other course search flow, and aggregator of other data

## Local setup

Requires [uv](https://docs.astral.sh/uv/), Node 22+ with pnpm, and Docker.

```sh
cp .env.example .env
make setup
make db     # Postgres + pgvector on :5432
make api    # http://localhost:8000/api/health
make web    # http://localhost:5173
```

Run `make check` before pushing; CI runs the same lint, typecheck, and tests.
