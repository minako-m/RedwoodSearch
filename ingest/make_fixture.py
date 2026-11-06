"""Build the frozen test snapshot: a small catalog subset that covers every data quirk.

Selection is deterministic (fixed rules + seeded shuffle), so rerunning on the same download gives
the same snapshot. Each chosen course is recorded in manifest.json with the reasons it was picked.

Usage: uv run python -m ingest.make_fixture [--raw DIR] [--out DIR]
"""

import argparse
import gzip
import json
import random
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

from ingest.parse import ARRANGED_COMPONENTS, parse_date

TARGET_SIZE = 200
SEED = 146

# Well-known courses, kept so tests and evals can refer to them by name.
ANCHORS = (
    "CS 106A", "CS 106B", "CS 107", "CS 109", "CS 161", "CS 221",
    "MATH 19", "MATH 51", "ECON 1", "PSYCH 1", "CHEM 31A", "PHYSICS 41", "SYMSYS 1",
)  # fmt: skip

# How many courses to keep per quirk tag. Tags not listed (per-value tags like `ger:WAY-FR`) need 1.
QUOTAS = {
    "arranged-only": 5,
    "time-tba": 8,
    "cross-listed": 8,
    "partial-quarter": 6,
    "multi-meeting": 6,
    "weekend": 4,
    "no-dates": 3,
    "days-no-time": 2,
    "time-no-days": 2,
    "end-no-start": 2,
    "variable-units": 5,
    "zero-units": 2,
    "section-units-outside-range": 3,
    "closed": 3,
    "remote": 3,
}
# Skip giant courses (hundreds of per-faculty sections) except via anchors.
MAX_COURSE_BYTES = 300_000


def course_name(course: ET.Element) -> str:
    return f"{course.findtext('subject')} {course.findtext('code')}"


def quirk_tags(course: ET.Element) -> set[str]:
    """Every data quirk this course exhibits, as short tags."""
    tags: set[str] = set()
    sections = course.findall("./sections/section")
    components = {s.findtext("component") or "" for s in sections}
    timed = False

    units_min = int(course.findtext("unitsMin") or 0)
    units_max = int(course.findtext("unitsMax") or 0)
    if units_min != units_max:
        tags.add("variable-units")
    if units_max == 0:
        tags.add("zero-units")
    for token in (course.findtext("gers") or "").split(","):
        if token.strip():
            tags.add(f"ger:{token.strip()}")
    career = course.findtext("./administrativeInformation/academicCareer")
    if career:
        tags.add(f"career:{career}")
    if course.findtext("remote") == "true":
        tags.add("remote")

    for section in sections:
        tags.add(f"component:{section.findtext('component')}")
        tags.add(f"mode:{section.findtext('instructionMode')}")
        tags.add(f"term:{(section.findtext('term') or '').rsplit(' ', 1)[-1]}")
        if section.findtext("enrollStatus") == "Closed":
            tags.add("closed")
        lo = (section.findtext("units") or "").split("-")[0]
        if lo.isdigit() and not units_min <= int(lo) <= units_max:
            tags.add("section-units-outside-range")
        schedules = section.findall("./schedules/schedule")
        if len(schedules) >= 2:
            tags.add("multi-meeting")
        for schedule in schedules:
            start = (schedule.findtext("startTime") or "").strip()
            end = (schedule.findtext("endTime") or "").strip()
            days = (schedule.findtext("days") or "").split()
            timed |= bool(start)
            if days and not start:
                tags.add("days-no-time")
            if start and not days:
                tags.add("time-no-days")
            if end and not start:
                tags.add("end-no-start")
            if {"Saturday", "Sunday"} & set(days):
                tags.add("weekend")
            first = parse_date(schedule.findtext("startDate"))
            last = parse_date(schedule.findtext("endDate"))
            if first is None or last is None:
                tags.add("no-dates")
            elif (last - first).days <= 42:
                tags.add("partial-quarter")

    if sections and components <= ARRANGED_COMPONENTS:
        tags.add("arranged-only")
    elif not timed:
        tags.add("time-tba")
    return tags


def course_id(course: ET.Element) -> str | None:
    return course.findtext("./sections/section/courseId")


def select(courses: dict[str, ET.Element]) -> dict[str, set[str]]:
    """Pick course names to keep, mapped to the reasons each was picked."""
    rng = random.Random(SEED)
    tags = {name: quirk_tags(c) for name, c in courses.items()}
    sizes = {name: len(ET.tostring(c)) for name, c in courses.items()}

    by_course_id: dict[str, set[str]] = defaultdict(set)
    for name, c in courses.items():
        if cid := course_id(c):
            by_course_id[cid].add(name)
    for group in by_course_id.values():
        if len(group) > 1:
            for name in group:
                tags[name].add("cross-listed")

    chosen: dict[str, set[str]] = defaultdict(set)

    def keep(name: str, reason: str) -> None:
        chosen[name].add(reason)
        # Keep cross-listing groups whole, so tests can check that they're merged.
        cid = course_id(courses[name])
        for partner in by_course_id.get(cid or "", set()) - {name}:
            chosen[partner].add(f"cross-listed with {name}")

    for name in ANCHORS:
        if name in courses:
            keep(name, "anchor")

    names = sorted(courses)
    rng.shuffle(names)
    small = [n for n in names if sizes[n] <= MAX_COURSE_BYTES]
    all_tags = sorted({t for ts in tags.values() for t in ts})
    for tag in all_tags:
        quota = QUOTAS.get(tag, 1)
        have = sum(1 for n in chosen if tag in tags[n])
        candidates = [n for n in small if tag in tags[n]] or [n for n in names if tag in tags[n]]
        for name in candidates:
            if have >= quota:
                break
            if name not in chosen:
                keep(name, tag)
                have += 1

    ordinary = [
        n
        for n in small
        if n not in chosen
        and "time-tba" not in tags[n]
        and "arranged-only" not in tags[n]
        and "career:UG" in tags[n]
    ]
    for name in ordinary:
        if len(chosen) >= TARGET_SIZE:
            break
        keep(name, "ordinary")

    return {name: chosen[name] | (tags[name] & {"cross-listed"}) for name in chosen}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=Path("data/raw/2026-2027"))
    parser.add_argument("--out", type=Path, default=Path("ingest/fixtures/2026-2027"))
    args = parser.parse_args()

    roots: dict[Path, ET.Element] = {}
    courses: dict[str, ET.Element] = {}
    source: dict[str, Path] = {}
    for path in sorted(args.raw.glob("*.xml.gz")):
        root = ET.fromstring(gzip.decompress(path.read_bytes()))
        roots[path] = root
        for c in root.iterfind("./courses/course"):
            courses[course_name(c)] = c
            source[course_name(c)] = path

    chosen = select(courses)

    args.out.mkdir(parents=True, exist_ok=True)
    for old in args.out.glob("*.xml.gz"):
        old.unlink()
    by_file: dict[Path, list[str]] = defaultdict(list)
    for name in chosen:
        by_file[source[name]].append(name)
    for path, names in sorted(by_file.items()):
        root = roots[path]
        container = root.find("courses")
        assert container is not None
        keep = set(names)
        for c in list(container):
            if course_name(c) not in keep:
                container.remove(c)
        body = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        (args.out / path.name).write_bytes(gzip.compress(body, mtime=0))

    manifest = {name: sorted(reasons) for name, reasons in sorted(chosen.items())}
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(chosen)} courses in {len(by_file)} department files → {args.out}")


if __name__ == "__main__":
    main()
