"""Apply numbered SQL migrations from db/migrations/ that haven't run yet, each in a transaction.

Usage: uv run python -m db.migrate [DATABASE_URL]
"""

import sys
from pathlib import Path

import psycopg

from db.settings import db_settings

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(conn: psycopg.Connection) -> list[str]:
    """Apply pending migrations in filename order. Returns the names of those applied."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " name text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
    )
    conn.commit()
    done = {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}
    applied = []
    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue
        with conn.transaction():
            conn.execute(path.read_text())  # a trusted file from this repo, never user input
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)
    return applied


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else db_settings.database_url
    with psycopg.connect(url) as conn:
        applied = migrate(conn)
    print(f"applied: {', '.join(applied)}" if applied else "schema up to date")


if __name__ == "__main__":
    main()
