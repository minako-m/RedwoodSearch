from pathlib import Path

import psycopg
import pytest

from ingest.load import load
from ingest.parse import Listing, load_listings

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "2026-2027"


@pytest.fixture(scope="module")
def snapshot() -> list[Listing]:
    return load_listings(FIXTURE_DIR)


def _count(db: psycopg.Connection, table: str) -> int:
    row = db.execute(f"SELECT count(*) FROM {table}").fetchone()  # noqa: S608  # test constant
    assert row is not None
    return int(row[0])


def test_load_snapshot_counts_match_parsed(db: psycopg.Connection, snapshot: list[Listing]) -> None:
    stats = load(db, snapshot)
    assert _count(db, "course_listings") == stats.listings == len(snapshot)
    assert _count(db, "sections") == stats.sections == sum(len(x.sections) for x in snapshot)
    assert _count(db, "meetings") == stats.meetings
    assert _count(db, "terms") == 4


def test_cross_listings_share_course_id(db: psycopg.Connection, snapshot: list[Listing]) -> None:
    load(db, snapshot)
    row = db.execute(
        "SELECT count(*) FROM (SELECT course_id FROM course_listings"
        " GROUP BY course_id HAVING count(*) > 1) AS groups"
    ).fetchone()
    assert row is not None and row[0] >= 8


def test_intro_psych_without_hard_prereqs(db: psycopg.Connection, snapshot: list[Listing]) -> None:
    load(db, snapshot)
    row = db.execute(
        "SELECT prereq_status, prereq_text FROM course_listings WHERE subject = %s AND code = %s",
        ("PSYCH", "1"),
    ).fetchone()
    assert row == ("none", None)


def test_reload_reuses_prereqs_only_for_unchanged_descriptions(
    db: psycopg.Connection, snapshot: list[Listing]
) -> None:
    load(db, snapshot)
    # Pretend a later (e.g. LLM) pass refined CS 106B; an unchanged description must keep it.
    db.execute(
        "UPDATE course_listings SET prereq_source = 'llm', prereq_status = 'consent'"
        " WHERE subject = 'CS' AND code = '106B'"
    )
    db.commit()
    stats = load(db, snapshot)
    assert stats.prereqs_reused == len(snapshot)
    row = db.execute(
        "SELECT prereq_source, prereq_status FROM course_listings"
        " WHERE subject = 'CS' AND code = '106B'"
    ).fetchone()
    assert row == ("llm", "consent")

    # A changed description gets re-extracted by the rules.
    changed = [
        x.model_copy(update={"description": x.description + " Updated."})
        if x.name == "CS 106B"
        else x
        for x in snapshot
    ]
    stats = load(db, changed)
    assert stats.prereqs_reused == len(snapshot) - 1
    row = db.execute(
        "SELECT prereq_source FROM course_listings WHERE subject = 'CS' AND code = '106B'"
    ).fetchone()
    assert row == ("rules",)


def test_reextract_recomputes_everything(db: psycopg.Connection, snapshot: list[Listing]) -> None:
    load(db, snapshot)
    assert load(db, snapshot, reextract=True).prereqs_reused == 0
