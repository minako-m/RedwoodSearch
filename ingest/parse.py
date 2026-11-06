"""Parse downloaded ExploreCourses XML into typed course listings, sections, and meetings.

Cleanup rules are applied here, so everything downstream sees normalized data: WAYS/GER tags fixed
up, cross-listing suffixes removed from titles, lost line breaks repaired, times as minutes since
midnight, days as a bitmask, and each section classified as scheduled / arranged / tba.
"""

import gzip
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

# Components that are always "by arrangement": one section per faculty member, no meeting time.
ARRANGED_COMPONENTS = frozenset({"INS", "T/D", "CLK"})
DAY_BITS = {
    "Monday": 1,
    "Tuesday": 2,
    "Wednesday": 4,
    "Thursday": 8,
    "Friday": 16,
    "Saturday": 32,
    "Sunday": 64,
}
# "(CS 152, INTLPOL 267)" at the end of a title. Other parentheses, like "(Quantitative)", stay.
CROSS_LISTING_SUFFIX = re.compile(r"\s*\((?:[A-Z&]+ \d+[A-Z0-9]*)(?:, [A-Z&]+ \d+[A-Z0-9]*)*\)\s*$")
# Line breaks that lost their backslash in the source data: "theater.nnConventional", ". nPREREQ".
LOST_NEWLINES = re.compile(
    r"(?<=[.:!?)])\s*n+(?=[A-Z0-9(])|(?<=\s)n+(?=[A-Z][a-z])|(?<=:)n+(?=[A-Za-z])"
)

Timing = Literal["scheduled", "arranged", "tba"]


class Instructor(BaseModel):
    sunet: str
    name: str
    first_name: str | None
    last_name: str | None
    role: str | None


class Meeting(BaseModel):
    days: int  # bitmask: Monday = 1, Tuesday = 2, ... Sunday = 64
    start_minute: int | None  # minutes since midnight; None when no time is published
    end_minute: int | None
    start_date: date | None
    end_date: date | None
    location: str | None
    instructors: list[Instructor]

    @property
    def is_timed(self) -> bool:
        return bool(self.days) and self.start_minute is not None


class Section(BaseModel):
    term_id: int
    term: str  # "2026-2027 Autumn"
    class_id: int
    section_number: str
    component: str
    units_min: int
    units_max: int
    timing: Timing
    instruction_mode: str | None
    enroll_status: str | None
    num_enrolled: int | None
    max_enrolled: int | None
    num_waitlist: int | None
    max_waitlist: int | None
    notes: str | None
    meetings: list[Meeting]


class Listing(BaseModel):
    subject: str
    code: str
    course_id: int  # shared by cross-listed listings
    academic_year: str
    title: str
    description: str
    units_min: int
    units_max: int
    gers: list[str]
    grading: str | None
    career: str | None
    final_exam: str | None
    remote: bool | None
    repeatable: bool | None
    sections: list[Section]

    @property
    def name(self) -> str:
        return f"{self.subject} {self.code}"


# --- field-level cleanup -------------------------------------------------------------------------


def _text(element: ET.Element, path: str) -> str | None:
    value = element.findtext(path)
    value = value.strip() if value else ""
    return value or None


def _int(element: ET.Element, path: str) -> int | None:
    value = _text(element, path)
    return int(value) if value and value.lstrip("-").isdigit() else None


def _bool(element: ET.Element, path: str) -> bool | None:
    value = _text(element, path)
    return {"true": True, "false": False}.get(value or "")


def parse_days(text: str | None) -> int:
    """'Tuesday Thursday' -> 10 (Tuesday bit + Thursday bit)."""
    return sum(DAY_BITS[day] for day in (text or "").split() if day in DAY_BITS)


def parse_time(text: str | None) -> int | None:
    """'3:00:00 PM' -> 900 (minutes since midnight)."""
    try:
        parsed = datetime.strptime((text or "").strip(), "%I:%M:%S %p")
    except ValueError:
        return None
    return parsed.hour * 60 + parsed.minute


def parse_date(text: str | None) -> date | None:
    """'Mar 29, 2027' -> date(2027, 3, 29)."""
    try:
        return datetime.strptime((text or "").strip(), "%b %d, %Y").date()
    except ValueError:
        return None


def parse_units(text: str | None, fallback: tuple[int, int]) -> tuple[int, int]:
    """'3-5' -> (3, 5); '4' -> (4, 4); '' -> fallback (the course's own range)."""
    match = re.fullmatch(r"(\d+)(?:-(\d+))?", (text or "").strip())
    if not match:
        return fallback
    low = int(match.group(1))
    return low, int(match.group(2) or low)


def normalize_ger(token: str) -> str:
    """Fix inconsistent tags: 'GER: DB-NatSci' -> 'GER:DB-NatSci', 'way_ce' -> 'WAY-CE'."""
    token = token.strip()
    if token.lower().startswith("way"):
        return "WAY-" + re.sub(r"^way[-_\s]*", "", token, flags=re.IGNORECASE).upper()
    if token.lower().startswith("ger"):
        return "GER:" + re.sub(r"^ger\s*:\s*", "", token, flags=re.IGNORECASE)
    return token


def clean_description(text: str) -> str:
    """Collapse whitespace and repair lost line breaks: "theater.nnWe" -> "theater. We"."""
    return " ".join(LOST_NEWLINES.sub(" ", text).split())


def strip_cross_listing(title: str) -> str:
    """'Trust and Safety (CS 152, INTLPOL 267)' -> 'Trust and Safety'."""
    return CROSS_LISTING_SUFFIX.sub("", title.strip())


def classify_timing(component: str, meetings: list[Meeting]) -> Timing:
    if component in ARRANGED_COMPONENTS:
        return "arranged"
    return "scheduled" if any(m.is_timed for m in meetings) else "tba"


# --- elements ------------------------------------------------------------------------------------


def _parse_meeting(schedule: ET.Element) -> Meeting:
    start = parse_time(schedule.findtext("startTime"))
    end = parse_time(schedule.findtext("endTime"))
    if start is None or end is None or end <= start:  # half a time range is no time at all
        start = end = None
    first, last = (
        parse_date(schedule.findtext("startDate")),
        parse_date(schedule.findtext("endDate")),
    )
    if first is None or last is None or last < first:
        first = last = None
    instructors = {}
    for ins in schedule.iterfind("./instructors/instructor"):
        sunet = _text(ins, "sunet")
        if sunet:
            instructors[sunet] = Instructor(
                sunet=sunet,
                name=_text(ins, "name") or sunet,
                first_name=_text(ins, "firstName"),
                last_name=_text(ins, "lastName"),
                role=_text(ins, "role"),
            )
    return Meeting(
        days=parse_days(schedule.findtext("days")),
        start_minute=start,
        end_minute=end,
        start_date=first,
        end_date=last,
        location=_text(schedule, "location"),
        instructors=list(instructors.values()),
    )


def _parse_section(section: ET.Element, course_units: tuple[int, int]) -> Section:
    component = _text(section, "component") or ""
    meetings = [_parse_meeting(s) for s in section.iterfind("./schedules/schedule")]
    units_min, units_max = parse_units(section.findtext("units"), course_units)
    return Section(
        term_id=_int(section, "termId") or 0,
        term=_text(section, "term") or "",
        class_id=_int(section, "classId") or 0,
        section_number=_text(section, "sectionNumber") or "",
        component=component,
        units_min=units_min,
        units_max=units_max,
        timing=classify_timing(component, meetings),
        instruction_mode=_text(section, "instructionMode"),
        enroll_status=_text(section, "enrollStatus"),
        num_enrolled=_int(section, "numEnrolled"),
        max_enrolled=_int(section, "maxEnrolled"),
        num_waitlist=_int(section, "numWaitlist"),
        max_waitlist=_int(section, "maxWaitlist"),
        notes=_text(section, "notes"),
        meetings=meetings,
    )


def parse_listings(xml: bytes) -> Iterator[Listing]:
    root = ET.fromstring(xml)
    for course in root.iterfind("./courses/course"):
        units = (_int(course, "unitsMin") or 0, _int(course, "unitsMax") or 0)
        units = (units[0], max(units))
        sections = [_parse_section(s, units) for s in course.iterfind("./sections/section")]
        course_id = _int(course, "./sections/section/courseId")
        if course_id is None:
            raise ValueError(f"{_text(course, 'subject')} {_text(course, 'code')} has no courseId")
        gers = (normalize_ger(g) for g in (course.findtext("gers") or "").split(","))
        yield Listing(
            subject=_text(course, "subject") or "",
            code=_text(course, "code") or "",
            course_id=course_id,
            academic_year=_text(course, "year") or "",
            title=strip_cross_listing(course.findtext("title") or ""),
            description=clean_description(course.findtext("description") or ""),
            units_min=units[0],
            units_max=units[1],
            gers=list(dict.fromkeys(g for g in gers if g)),
            grading=_text(course, "grading"),
            career=_text(course, "./administrativeInformation/academicCareer"),
            final_exam=_text(course, "./administrativeInformation/finalExamFlag"),
            remote=_bool(course, "remote"),
            repeatable=_bool(course, "repeatable"),
            sections=sections,
        )


def sort_key(listing: Listing) -> tuple[str, int, str]:
    """Order like the catalog: by subject, then course number numerically (CS 9 before CS 106B)."""
    match = re.match(r"(\d*)(.*)", listing.code)
    number, suffix = match.groups() if match else ("", listing.code)
    return (listing.subject, int(number) if number else 0, suffix)


def load_listings(raw_dir: Path) -> list[Listing]:
    """All listings from a directory of `<DEPT>.xml.gz` files, in catalog order."""
    listings = [
        listing
        for path in raw_dir.glob("*.xml.gz")
        for listing in parse_listings(gzip.decompress(path.read_bytes()))
    ]
    return sorted(listings, key=sort_key)
