"""Read-only catalog queries. Every value is passed as a parameter, never pasted into SQL text."""

from collections import defaultdict

import psycopg
from psycopg.rows import dict_row

from api.models import (
    CourseDetail,
    CourseSummary,
    InstructorOut,
    MeetingOut,
    Prereq,
    SectionOut,
    TermSections,
)

DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")  # bit 0 = Monday


def day_names(mask: int) -> list[str]:
    return [name for bit, name in enumerate(DAY_NAMES) if mask & (1 << bit)]


def list_courses(conn: psycopg.Connection) -> list[CourseSummary]:
    rows = conn.cursor(row_factory=dict_row).execute(
        "SELECT l.subject, l.code, l.title, l.units_min, l.units_max, l.gers, l.career,"
        "  ARRAY(SELECT q FROM unnest(ARRAY['Autumn', 'Winter', 'Spring', 'Summer'])"
        "        WITH ORDINALITY AS u(q, i)"
        "        WHERE q IN (SELECT t.quarter FROM sections s JOIN terms t ON t.id = s.term_id"
        "                    WHERE s.listing_id = l.id)"
        "        ORDER BY i) AS terms"
        " FROM course_listings l"
        # Catalog order: subject, then course number numerically (CS 9 before CS 106B), then suffix.
        " ORDER BY l.subject, substring(l.code from '^[0-9]+')::int NULLS FIRST,"
        "  substring(l.code from '^[0-9]*(.*)$')"
    )
    return [CourseSummary(**row) for row in rows]


def get_course(conn: psycopg.Connection, subject: str, code: str) -> CourseDetail | None:
    cur = conn.cursor(row_factory=dict_row)
    listing = cur.execute(
        "SELECT * FROM course_listings WHERE subject = %s AND code = %s", (subject, code)
    ).fetchone()
    if listing is None:
        return None

    cross_listings = [
        row["name"]
        for row in cur.execute(
            "SELECT subject || ' ' || code AS name FROM course_listings"
            " WHERE course_id = %s AND id <> %s ORDER BY subject, code",
            (listing["course_id"], listing["id"]),
        )
    ]

    sections = cur.execute(
        "SELECT s.*, t.name AS term, t.quarter FROM sections s JOIN terms t ON t.id = s.term_id"
        " WHERE s.listing_id = %s ORDER BY s.term_id, s.timing <> 'scheduled', s.section_number",
        (listing["id"],),
    ).fetchall()
    section_ids = [s["id"] for s in sections]

    instructors: dict[int, list[InstructorOut]] = defaultdict(list)
    for row in cur.execute(
        "SELECT mi.meeting_id, i.sunet, i.name, mi.role FROM meeting_instructors mi"
        " JOIN instructors i ON i.sunet = mi.sunet JOIN meetings m ON m.id = mi.meeting_id"
        " WHERE m.section_id = ANY(%s) ORDER BY mi.role = 'PI' DESC, i.name",
        (section_ids,),
    ):
        instructors[row["meeting_id"]].append(
            InstructorOut(sunet=row["sunet"], name=row["name"], role=row["role"])
        )

    meetings: dict[int, list[MeetingOut]] = defaultdict(list)
    for row in cur.execute(
        "SELECT * FROM meetings WHERE section_id = ANY(%s) ORDER BY id", (section_ids,)
    ):
        meetings[row["section_id"]].append(
            MeetingOut(
                days=day_names(row["days"]),
                start_minute=row["start_minute"],
                end_minute=row["end_minute"],
                start_date=row["start_date"].isoformat() if row["start_date"] else None,
                end_date=row["end_date"].isoformat() if row["end_date"] else None,
                location=row["location"],
                instructors=instructors[row["id"]],
            )
        )

    terms: dict[str, TermSections] = {}
    for s in sections:
        term = terms.setdefault(
            s["term"], TermSections(term=s["term"], quarter=s["quarter"], sections=[])
        )
        term.sections.append(
            SectionOut(
                class_id=s["class_id"],
                section_number=s["section_number"],
                component=s["component"],
                units_min=s["units_min"],
                units_max=s["units_max"],
                timing=s["timing"],
                instruction_mode=s["instruction_mode"],
                enroll_status=s["enroll_status"],
                num_enrolled=s["num_enrolled"],
                max_enrolled=s["max_enrolled"],
                num_waitlist=s["num_waitlist"],
                max_waitlist=s["max_waitlist"],
                notes=s["notes"],
                meetings=meetings[s["id"]],
            )
        )

    return CourseDetail(
        subject=listing["subject"],
        code=listing["code"],
        title=listing["title"],
        description=listing["description"],
        units_min=listing["units_min"],
        units_max=listing["units_max"],
        gers=listing["gers"],
        grading=listing["grading"],
        career=listing["career"],
        final_exam=listing["final_exam"],
        remote=listing["remote"],
        repeatable=listing["repeatable"],
        prereq=Prereq(
            status=listing["prereq_status"],
            text=listing["prereq_text"],
            courses=listing["prereq_courses"],
        ),
        cross_listings=cross_listings,
        terms=list(terms.values()),
    )
