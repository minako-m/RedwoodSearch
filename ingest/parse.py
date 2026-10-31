"""Parse downloaded ExploreCourses XML into course summaries."""

import gzip
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path

from pydantic import BaseModel

TERM_ORDER = ("Autumn", "Winter", "Spring", "Summer")


class CourseSummary(BaseModel):
    subject: str
    code: str
    title: str
    units_min: int
    units_max: int
    gers: list[str]
    terms: list[str]  # quarters with at least one section, in academic-year order
    career: str | None


def parse_courses(xml: bytes) -> Iterator[CourseSummary]:
    root = ET.fromstring(xml)
    for course in root.iterfind("./courses/course"):
        sections = course.findall("./sections/section")
        terms = {(s.findtext("term") or "").rsplit(" ", 1)[-1] for s in sections}
        yield CourseSummary(
            subject=course.findtext("subject") or "",
            code=course.findtext("code") or "",
            title=(course.findtext("title") or "").strip(),
            units_min=int(course.findtext("unitsMin") or 0),
            units_max=int(course.findtext("unitsMax") or 0),
            gers=[g.strip() for g in (course.findtext("gers") or "").split(",") if g.strip()],
            terms=[t for t in TERM_ORDER if t in terms],
            career=course.findtext("./administrativeInformation/academicCareer"),
        )


def sort_key(course: CourseSummary) -> tuple[str, int, str]:
    """Order like the catalog: by subject, then course number numerically (CS 9 before CS 106B)."""
    match = re.match(r"(\d*)(.*)", course.code)
    number, suffix = match.groups() if match else ("", course.code)
    return (course.subject, int(number) if number else 0, suffix)


def load_catalog(raw_dir: Path) -> list[CourseSummary]:
    """All courses from a directory of `<DEPT>.xml.gz` files, in catalog order."""
    courses = [
        course
        for path in raw_dir.glob("*.xml.gz")
        for course in parse_courses(gzip.decompress(path.read_bytes()))
    ]
    return sorted(courses, key=sort_key)
