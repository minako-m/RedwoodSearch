"""Load parsed catalog data into Postgres, replacing what's there in one transaction.

Prerequisite fields are derived from descriptions and can be expensive to produce (a later pass
may use an LLM), so they're carried over from the previous load for any listing whose description
hasn't changed. Pass --reextract to recompute them all, e.g. after improving the extraction rules.

Usage: uv run python -m ingest.load [--source DIR] [--database-url URL] [--reextract]
"""

import argparse
import hashlib
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg import sql

from db.migrate import migrate
from db.settings import db_settings
from ingest.parse import Listing, load_listings
from ingest.prereqs import Prereq, extract_prereqs

Row = tuple[object, ...]

CATALOG_TABLES = (
    "meeting_instructors",
    "meetings",
    "sections",
    "course_listings",
    "instructors",
    "terms",
)
TERM_COLUMNS = ("id", "name", "academic_year", "quarter")
INSTRUCTOR_COLUMNS = ("sunet", "name", "first_name", "last_name")
LISTING_COLUMNS = (
    "id", "subject", "code", "course_id", "academic_year", "title", "description",
    "description_hash", "units_min", "units_max", "gers", "grading", "career", "final_exam",
    "remote", "repeatable", "prereq_status", "prereq_text", "prereq_courses", "prereq_source",
)  # fmt: skip
SECTION_COLUMNS = (
    "id", "listing_id", "term_id", "class_id", "section_number", "component", "units_min",
    "units_max", "timing", "instruction_mode", "enroll_status", "num_enrolled", "max_enrolled",
    "num_waitlist", "max_waitlist", "notes",
)  # fmt: skip
MEETING_COLUMNS = (
    "id", "section_id", "days", "start_minute", "end_minute", "start_date", "end_date", "location",
)  # fmt: skip
TEACHING_COLUMNS = ("meeting_id", "sunet", "role")


@dataclass(frozen=True)
class LoadStats:
    listings: int
    sections: int
    meetings: int
    instructors: int
    prereqs_reused: int


def description_hash(description: str) -> str:
    return hashlib.sha256(description.encode()).hexdigest()


def _existing_prereqs(
    conn: psycopg.Connection,
) -> dict[tuple[str, str, str, str], tuple[Prereq, str]]:
    """Prerequisite fields from the current load, keyed by (subject, code, year, description)."""
    rows = conn.execute(
        "SELECT subject, code, academic_year, description_hash,"
        " prereq_status, prereq_text, prereq_courses, prereq_source FROM course_listings"
    )
    return {
        (subject, code, year, digest): (Prereq(status, text, courses), source)
        for subject, code, year, digest, status, text, courses, source in rows
    }


def load(conn: psycopg.Connection, listings: list[Listing], reextract: bool = False) -> LoadStats:
    known_subjects = frozenset(listing.subject for listing in listings)
    previous = {} if reextract else _existing_prereqs(conn)
    reused = 0

    terms: dict[int, str] = {}
    instructors: dict[str, tuple[str, str | None, str | None]] = {}
    listing_rows: list[Row] = []
    section_rows: list[Row] = []
    meeting_rows: list[Row] = []
    teaching_rows: list[Row] = []

    for listing_id, listing in enumerate(listings, 1):
        digest = description_hash(listing.description)
        key = (listing.subject, listing.code, listing.academic_year, digest)
        if key in previous:
            prereq, source = previous[key]
            reused += 1
        else:
            prereq, source = (
                extract_prereqs(listing.description, listing.subject, known_subjects),
                "rules",
            )
        listing_rows.append((
            listing_id, listing.subject, listing.code, listing.course_id, listing.academic_year,
            listing.title, listing.description, digest, listing.units_min, listing.units_max,
            listing.gers, listing.grading, listing.career, listing.final_exam, listing.remote,
            listing.repeatable, prereq.status, prereq.text, prereq.courses, source,
        ))  # fmt: skip
        for section in listing.sections:
            terms[section.term_id] = section.term
            section_id = len(section_rows) + 1
            section_rows.append((
                section_id, listing_id, section.term_id, section.class_id, section.section_number,
                section.component, section.units_min, section.units_max, section.timing,
                section.instruction_mode, section.enroll_status, section.num_enrolled,
                section.max_enrolled, section.num_waitlist, section.max_waitlist, section.notes,
            ))  # fmt: skip
            for meeting in section.meetings:
                meeting_id = len(meeting_rows) + 1
                meeting_rows.append((
                    meeting_id, section_id, meeting.days, meeting.start_minute, meeting.end_minute,
                    meeting.start_date, meeting.end_date, meeting.location,
                ))  # fmt: skip
                for ins in meeting.instructors:
                    instructors[ins.sunet] = (ins.name, ins.first_name, ins.last_name)
                    teaching_rows.append((meeting_id, ins.sunet, ins.role))

    term_rows: list[Row] = [
        (term_id, name, name.rsplit(" ", 1)[0], name.rsplit(" ", 1)[-1])
        for term_id, name in terms.items()
    ]
    instructor_rows: list[Row] = [(sunet, *names) for sunet, names in instructors.items()]

    with conn.transaction(), conn.cursor() as cur:
        tables = sql.SQL(", ").join(map(sql.Identifier, CATALOG_TABLES))
        cur.execute(sql.SQL("TRUNCATE {} RESTART IDENTITY").format(tables))
        _copy(cur, "terms", TERM_COLUMNS, term_rows)
        _copy(cur, "instructors", INSTRUCTOR_COLUMNS, instructor_rows)
        _copy(cur, "course_listings", LISTING_COLUMNS, listing_rows)
        _copy(cur, "sections", SECTION_COLUMNS, section_rows)
        _copy(cur, "meetings", MEETING_COLUMNS, meeting_rows)
        _copy(cur, "meeting_instructors", TEACHING_COLUMNS, teaching_rows)
        # Rows were inserted with explicit ids; move each id counter past them.
        for table in ("course_listings", "sections", "meetings"):
            cur.execute(
                sql.SQL(
                    "SELECT setval(pg_get_serial_sequence(%s, 'id'), GREATEST(max(id), 1)) FROM {}"
                ).format(sql.Identifier(table)),
                (table,),
            )

    return LoadStats(
        listings=len(listing_rows),
        sections=len(section_rows),
        meetings=len(meeting_rows),
        instructors=len(instructor_rows),
        prereqs_reused=reused,
    )


def _copy(cur: psycopg.Cursor, table: str, columns: tuple[str, ...], rows: list[Row]) -> None:
    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, columns))
    )
    with cur.copy(statement) as copy:
        for row in rows:
            copy.write_row(row)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=Path("ingest/fixtures/2026-2027"))
    parser.add_argument("--database-url", default=db_settings.database_url)
    parser.add_argument("--reextract", action="store_true", help="recompute all prerequisites")
    args = parser.parse_args()

    listings = load_listings(args.source)
    with psycopg.connect(args.database_url) as conn:
        migrate(conn)
        stats = load(conn, listings, reextract=args.reextract)
    print(
        f"loaded {stats.listings} listings, {stats.sections} sections, {stats.meetings} meetings,"
        f" {stats.instructors} instructors from {args.source}"
        f" ({stats.prereqs_reused} prerequisite results reused)"
    )


if __name__ == "__main__":
    main()
