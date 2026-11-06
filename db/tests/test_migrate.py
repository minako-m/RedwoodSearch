import psycopg
import pytest

from db.migrate import migrate


def test_migrate_is_idempotent(db: psycopg.Connection) -> None:
    assert migrate(db) == []  # the session fixture already applied everything
    tables = {
        row[0] for row in db.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    }
    assert {"terms", "course_listings", "sections", "meetings", "instructors"} <= tables


def test_meetings_reject_end_before_start(db: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute(
            "INSERT INTO meetings (section_id, days, start_minute, end_minute)"
            " VALUES (1, 2, 900, 800)"
        )
    db.rollback()


def test_meetings_reject_half_a_time_range(db: psycopg.Connection) -> None:
    with pytest.raises(psycopg.errors.CheckViolation):
        db.execute("INSERT INTO meetings (section_id, days, start_minute) VALUES (1, 2, 900)")
    db.rollback()
