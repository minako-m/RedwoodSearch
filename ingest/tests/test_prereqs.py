import pytest

from ingest.prereqs import extract_prereqs, mentioned_courses

KNOWN = frozenset({"CS", "PSYCH", "MATH", "STATS", "ENGR", "CEE", "MATSCI"})


@pytest.mark.parametrize(
    ("description", "subject", "status", "courses"),
    [
        ("An introduction to the field.", "PSYCH", "none", []),
        ("Covers memory. Required prerequisite: PSYCH 1.", "PSYCH", "required", ["PSYCH 1"]),
        ("Covers development. Recommended: PSYCH 1", "PSYCH", "recommended", ["PSYCH 1"]),
        ("Taught at an introductory level, without prerequisites.", "PSYCH", "none", []),
        ("PREREQUISITES: None.", "CS", "none", []),
        ("Prerequisite: consent of instructor.", "CS", "consent", []),
        ("Enrollment limited; permission of the instructor required.", "CS", "consent", []),
        ("Prerequisite: CS 106B or consent of instructor.", "CS", "required", ["CS 106B"]),
        ("Corequisite: 60.", "PSYCH", "required", ["PSYCH 60"]),
        (
            "Prerequisites: a clerkship in medicine is strongly recommended.",
            "CS",
            "recommended",
            [],
        ),
        # The strictest sentence wins.
        ("Recommended: MATH 51. Prerequisite: CS 106B.", "CS", "required", ["CS 106B"]),
        # Missing space after the period still splits sentences.
        ("Two quarters of work.Prerequisite: CS 107.", "CS", "required", ["CS 107"]),
    ],
)
def test_extract_prereqs(description: str, subject: str, status: str, courses: list[str]) -> None:
    prereq = extract_prereqs(description, subject, KNOWN)
    assert prereq.status == status
    assert prereq.courses == courses


def test_extract_prereqs_keeps_source_sentence() -> None:
    prereq = extract_prereqs("Covers memory. Required prerequisite: PSYCH 1.", "PSYCH", KNOWN)
    assert prereq.text == "Required prerequisite: PSYCH 1."


@pytest.mark.parametrize(
    ("text", "subject", "expected"),
    [
        ("Prerequisite: 106B or 106X; 103 or 103B; 109 or STATS 116.", "CS",
         ["CS 106B", "CS 106X", "CS 103", "CS 103B", "CS 109", "STATS 116"]),
        ("Prerequisite: 101A and ENGR 14.", "CEE", ["CEE 101A", "ENGR 14"]),
        ("Recommended: MATH 113, 115, or equivalent.", "CS", ["MATH 113", "MATH 115"]),
        ("Prerequisites: MATSCI 193/203.", "MATSCI", ["MATSCI 193", "MATSCI 203"]),
        ("Prerequisite: Math 51 or CS106B.", "PSYCH", ["MATH 51", "CS 106B"]),
        # Non-departments and quantities aren't courses.
        ("Prerequisite: Year 3 standing, or 2 quarters of study.", "CS", []),
    ],
)  # fmt: skip
def test_mentioned_courses(text: str, subject: str, expected: list[str]) -> None:
    assert mentioned_courses(text, subject, KNOWN) == expected
