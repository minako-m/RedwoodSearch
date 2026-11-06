import gzip
from datetime import date
from pathlib import Path

import pytest

from ingest.parse import (
    Meeting,
    classify_timing,
    clean_description,
    load_listings,
    normalize_ger,
    parse_days,
    parse_listings,
    parse_time,
    parse_units,
    strip_cross_listing,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "2026-2027"

COURSE_XML = b"""<xml><courses>
  <course>
    <year>2026-2027</year>
    <subject>CS</subject><code>106B</code>
    <title> Programming Abstractions (ENGR 70B) </title>
    <description>Abstraction and recursion.nnPrerequisite: CS 106A.</description>
    <unitsMin>3</unitsMin><unitsMax>5</unitsMax>
    <gers>WAY-FR, GER: DB-EngrAppSci, way_ce</gers>
    <grading>Letter or Credit/No Credit</grading>
    <remote>false</remote>
    <administrativeInformation>
      <academicCareer>UG</academicCareer><finalExamFlag>Y</finalExamFlag>
    </administrativeInformation>
    <sections>
      <section>
        <classId>1234</classId><term>2026-2027 Autumn</term><termId>1272</termId>
        <units>5</units><sectionNumber>01</sectionNumber><component>LEC</component>
        <numEnrolled>300</numEnrolled><maxEnrolled>400</maxEnrolled><enrollStatus>Open</enrollStatus>
        <courseId>105750</courseId>
        <schedules><schedule>
          <startDate>Sep 21, 2026</startDate><endDate>Dec 4, 2026</endDate>
          <startTime>11:30:00 AM</startTime><endTime>12:20:00 PM</endTime>
          <location>NVIDIA Auditorium</location>
          <days> Monday Wednesday Friday </days>
          <instructors><instructor>
            <name>Schwarz, K.</name><firstName>Keith</firstName><lastName>Schwarz</lastName>
            <sunet>htiek</sunet><role>PI</role>
          </instructor></instructors>
        </schedule></schedules>
      </section>
      <section>
        <classId>1235</classId><term>2026-2027 Autumn</term><termId>1272</termId>
        <units></units><sectionNumber>02</sectionNumber><component>DIS</component>
        <courseId>105750</courseId>
        <schedules><schedule><startTime></startTime><endTime></endTime><days></days></schedule></schedules>
      </section>
    </sections>
  </course>
</courses></xml>"""


def test_parse_listings_full_course() -> None:
    [listing] = parse_listings(COURSE_XML)
    assert listing.name == "CS 106B"
    assert listing.course_id == 105750
    assert listing.title == "Programming Abstractions"
    assert listing.description == "Abstraction and recursion. Prerequisite: CS 106A."
    assert (listing.units_min, listing.units_max) == (3, 5)
    assert listing.gers == ["WAY-FR", "GER:DB-EngrAppSci", "WAY-CE"]
    assert (listing.career, listing.final_exam, listing.remote) == ("UG", "Y", False)

    lecture, discussion = listing.sections
    assert (lecture.term_id, lecture.class_id, lecture.component) == (1272, 1234, "LEC")
    assert (lecture.units_min, lecture.units_max) == (5, 5)
    assert lecture.timing == "scheduled"
    assert (lecture.num_enrolled, lecture.max_enrolled) == (300, 400)
    [meeting] = lecture.meetings
    assert meeting.days == 1 | 4 | 16
    assert (meeting.start_minute, meeting.end_minute) == (690, 740)
    assert (meeting.start_date, meeting.end_date) == (date(2026, 9, 21), date(2026, 12, 4))
    assert meeting.location == "NVIDIA Auditorium"
    assert [(i.sunet, i.role) for i in meeting.instructors] == [("htiek", "PI")]

    # Blank section units fall back to the course's range; no time means TBA.
    assert (discussion.units_min, discussion.units_max) == (3, 5)
    assert discussion.timing == "tba"
    assert discussion.meetings[0].start_minute is None


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("12:00:00 AM", 0),
        ("9:30:00 AM", 570),
        ("12:00:00 PM", 720),
        ("3:00:00 PM", 900),
        ("", None),
    ],
)
def test_parse_time(text: str, minutes: int | None) -> None:
    assert parse_time(text) == minutes


def test_parse_days() -> None:
    assert parse_days("Tuesday Thursday") == 2 | 8
    assert parse_days("Sunday Saturday") == 64 | 32
    assert parse_days("") == 0


def test_parse_units() -> None:
    assert parse_units("3-5", (1, 1)) == (3, 5)
    assert parse_units("4", (1, 1)) == (4, 4)
    assert parse_units("", (2, 3)) == (2, 3)


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("WAY-FR", "WAY-FR"),
        ("way_ce", "WAY-CE"),
        ("GER: DB-NatSci", "GER:DB-NatSci"),
        ("GER:DB-Hum", "GER:DB-Hum"),
        ("Writing 2", "Writing 2"),
    ],
)
def test_normalize_ger(raw: str, normalized: str) -> None:
    assert normalize_ger(raw) == normalized


def test_strip_cross_listing_keeps_other_parentheses() -> None:
    assert strip_cross_listing("Trust and Safety (CS 152, INTLPOL 267)") == "Trust and Safety"
    assert strip_cross_listing("Worldbuilding (CSRE 194DS9, PWR 194DS9)") == "Worldbuilding"
    assert (
        strip_cross_listing("Economic Analysis I (Quantitative)")
        == "Economic Analysis I (Quantitative)"
    )


def test_clean_description_repairs_lost_newlines() -> None:
    assert clean_description("theater. nnConventional wisdom") == "theater. Conventional wisdom"
    assert clean_description("Prerequisites:nCS and math") == "Prerequisites: CS and math"
    assert clean_description("An unknown network.") == "An unknown network."


def test_classify_timing() -> None:
    timed = Meeting(
        days=2, start_minute=600, end_minute=650, start_date=None, end_date=None,
        location=None, instructors=[],
    )  # fmt: skip
    untimed = timed.model_copy(update={"start_minute": None, "end_minute": None})
    assert classify_timing("INS", [timed]) == "arranged"
    assert classify_timing("LEC", [untimed, timed]) == "scheduled"
    assert classify_timing("LEC", [untimed]) == "tba"
    assert classify_timing("SEM", []) == "tba"


def test_snapshot_parses_with_all_three_timings() -> None:
    listings = load_listings(FIXTURE_DIR)
    timings = {s.timing for listing in listings for s in listing.sections}
    assert timings == {"scheduled", "arranged", "tba"}
    for listing in listings:
        for section in listing.sections:
            for meeting in section.meetings:
                if meeting.start_minute is not None:
                    assert meeting.end_minute is not None
                    assert meeting.start_minute < meeting.end_minute


def _course(subject: str, code: str) -> bytes:
    return (
        f"<course><subject>{subject}</subject><code>{code}</code><sections><section>"
        f"<courseId>1</courseId></section></sections></course>"
    ).encode()


def test_load_listings_sorts_by_subject_then_number(tmp_path: Path) -> None:
    cs = b"<xml><courses>" + _course("CS", "106B") + _course("CS", "9") + _course("CS", "106A")
    (tmp_path / "CS.xml.gz").write_bytes(gzip.compress(cs + b"</courses></xml>"))
    aa = b"<xml><courses>" + _course("AA", "100") + b"</courses></xml>"
    (tmp_path / "AA.xml.gz").write_bytes(gzip.compress(aa))

    names = [f"{c.subject} {c.code}" for c in load_listings(tmp_path)]
    assert names == ["AA 100", "CS 9", "CS 106A", "CS 106B"]
