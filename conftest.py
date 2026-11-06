"""Shared pytest fixtures. Database tests use TEST_DATABASE_URL, wiped every test session."""

from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

from db.migrate import migrate
from db.settings import db_settings


def _ensure_database_exists(url: str) -> None:
    """Create the test database on first use, via the server's default database."""
    info = psycopg.conninfo.conninfo_to_dict(url)
    name = str(info["dbname"])
    admin_url = psycopg.conninfo.make_conninfo(url, dbname="postgres")
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone()
        if not exists:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture(scope="session")
def migrated_db_url() -> str:
    url = db_settings.test_database_url
    try:
        _ensure_database_exists(url)
    except psycopg.OperationalError as e:
        pytest.fail(f"Test database unreachable ({e}). Start it with `make db`.", pytrace=False)
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("DROP SCHEMA public CASCADE")
        conn.execute("CREATE SCHEMA public")
    with psycopg.connect(url) as conn:
        migrate(conn)
    return url


@pytest.fixture
def db(migrated_db_url: str) -> Iterator[psycopg.Connection]:
    with psycopg.connect(migrated_db_url) as conn:
        yield conn
