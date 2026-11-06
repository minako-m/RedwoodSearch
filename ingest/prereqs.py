"""Extract prerequisite information from course descriptions with pattern rules.

ExploreCourses has no prerequisite field; requirements are written into the description in many
styles ("Prerequisite: CS 106B.", "Recommended: PSYCH 1", "...without prerequisites."). Each
sentence is classified, and the strictest classification wins:

    required > consent > recommended > none

Only hard requirements count as prerequisites: a course with only recommended preparation is
treated as having none when students filter for "no prerequisites".
"""

import re
from dataclasses import dataclass, field
from typing import Literal

PrereqStatus = Literal["none", "recommended", "consent", "required"]
RANK: dict[PrereqStatus, int] = {"none": 0, "recommended": 1, "consent": 2, "required": 3}

# Sentence breaks, including the common missing space: "...two quarters.Prerequisite: ...".
_SENTENCE_END = re.compile(r"(?<=[.;!?])\s+(?=[A-Z(])|(?<=[a-z][.;])(?=[A-Z][a-z])")
_EXPLICIT_NONE = re.compile(
    r"\b(no|without)\s+(formal\s+|specific\s+|course\s+)?pre-?req|"
    r"\bpre-?req[a-z]*\s*:?\s*(none|n/a)\b",
    re.IGNORECASE,
)
_RECOMMENDED_PREREQ = re.compile(
    r"\brecommended\s+pre-?req|\bpre-?req[a-z]*\s*(\(|:)?\s*(strongly\s+)?(recommended|suggested)|"
    r"^\s*(strongly\s+)?(recommended|suggested)( background| preparation)?\s*:|"
    r"\bpre-?req[a-z]*\s*:[^;]*\brecommended\W*$",  # "Prerequisites: X is strongly recommended."
    re.IGNORECASE,
)
_REQUIRED = re.compile(
    r"\bpre-?req|\bco-?req|\bmust have (taken|completed)|\bprior completion of|"
    r"\brequires? (completion|prior)",
    re.IGNORECASE,
)
_CONSENT = re.compile(
    r"\bconsent of (the )?instructor|\binstructor('s)? (consent|permission)|"
    r"\bpermission of (the )?instructor",
    re.IGNORECASE,
)
_RECOMMENDED = re.compile(r"\b(recommended|suggested|helpful)\b", re.IGNORECASE)
# "CS 106B", "CS106B", "Math 51", or a bare number continuing a list ("MATH 113, 115"; "101A and
# ENGR 14"), which belongs to the last subject mentioned, or to the course's own subject.
_COURSE_CODE = re.compile(
    r"\b(?:(?P<subject>[A-Z][A-Za-z&]{1,9})\s?|(?<=[:;,/]\s)|(?<=[:;,/])|(?<=\band\s)|(?<=\bor\s))"
    r"(?P<number>\d{1,3}[A-Z]{0,3}\d?)\b"
    r"(?!\s*(?:units?|quarters?|years?|hours?|credits?|weeks?|days?|students|%))"
)


@dataclass(frozen=True)
class Prereq:
    status: PrereqStatus
    text: str | None = None  # the sentence(s) the status came from
    courses: list[str] = field(default_factory=list)  # e.g. ["CS 106B"]


def mentioned_courses(text: str, own_subject: str, known_subjects: frozenset[str]) -> list[str]:
    """Course codes in `text`: 'Math 51 or CS106B' -> ['MATH 51', 'CS 106B'].

    Words that aren't real departments ("Year 3") are ignored. Bare numbers take the subject of the
    previous code in the sentence, or `own_subject` if there is none.
    """
    found = []
    current = own_subject
    for match in _COURSE_CODE.finditer(text):
        subject = match.group("subject")
        if subject is not None:
            if subject.upper() not in known_subjects:
                continue
            current = subject.upper()
        found.append(f"{current} {match.group('number')}")
    return list(dict.fromkeys(found))


def classify_sentence(
    sentence: str, own_subject: str, known: frozenset[str]
) -> PrereqStatus | None:
    """What one sentence says about prerequisites, or None if it says nothing."""
    if _EXPLICIT_NONE.search(sentence):
        return "none"
    if _RECOMMENDED_PREREQ.search(sentence):
        return "recommended"
    if _REQUIRED.search(sentence):
        # "Prerequisite: consent of instructor." is a consent gate, not a course requirement.
        if _CONSENT.search(sentence) and not mentioned_courses(sentence, own_subject, known):
            return "consent"
        return "required"
    if _CONSENT.search(sentence):
        return "consent"
    if _RECOMMENDED.search(sentence) and mentioned_courses(sentence, own_subject, known):
        return "recommended"
    return None


def extract_prereqs(description: str, own_subject: str, known_subjects: frozenset[str]) -> Prereq:
    found: list[tuple[PrereqStatus, str]] = []
    for sentence in _SENTENCE_END.split(description):
        status = classify_sentence(sentence, own_subject, known_subjects)
        if status is not None:
            found.append((status, sentence.strip()))
    if not found:
        return Prereq("none")
    top = max((status for status, _ in found), key=RANK.__getitem__)
    text = " ".join(s for status, s in found if status == top)
    courses = (
        mentioned_courses(text, own_subject, known_subjects)
        if top in ("required", "recommended")
        else []
    )
    return Prereq(top, text, courses)
