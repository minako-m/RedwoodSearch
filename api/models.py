"""Response shapes. web/src/api.ts mirrors these; keep the two in sync."""

from typing import Literal

from pydantic import BaseModel

PrereqStatus = Literal["none", "recommended", "consent", "required"]
Timing = Literal["scheduled", "arranged", "tba"]


class CourseSummary(BaseModel):
    """One row of the course list."""

    subject: str
    code: str
    title: str
    units_min: int
    units_max: int
    gers: list[str]
    terms: list[str]  # quarters with at least one section, in academic-year order
    career: str | None


class Prereq(BaseModel):
    status: PrereqStatus
    text: str | None  # the description sentence the status came from
    courses: list[str]


class InstructorOut(BaseModel):
    sunet: str
    name: str
    role: str | None


class MeetingOut(BaseModel):
    days: list[str]  # ["Tue", "Thu"]
    start_minute: int | None  # minutes since midnight
    end_minute: int | None
    start_date: str | None  # ISO date, e.g. "2026-09-21"
    end_date: str | None
    location: str | None
    instructors: list[InstructorOut]


class SectionOut(BaseModel):
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
    meetings: list[MeetingOut]


class TermSections(BaseModel):
    term: str  # "2026-2027 Autumn"
    quarter: str
    sections: list[SectionOut]


class CourseDetail(BaseModel):
    subject: str
    code: str
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
    prereq: Prereq
    cross_listings: list[str]  # other names for the same course, e.g. ["COMM 122"]
    terms: list[TermSections]
