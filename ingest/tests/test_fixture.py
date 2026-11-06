"""Guards the frozen snapshot: it must load, match its manifest, and cover every data quirk."""

import gzip
import json
import xml.etree.ElementTree as ET
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from ingest.make_fixture import ANCHORS, QUOTAS, course_id, quirk_tags
from ingest.parse import load_catalog

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "2026-2027"


def _manifest() -> dict[str, list[str]]:
    manifest: dict[str, list[str]] = json.loads((FIXTURE_DIR / "manifest.json").read_text())
    return manifest


def _courses() -> Iterator[ET.Element]:
    for path in FIXTURE_DIR.glob("*.xml.gz"):
        yield from ET.fromstring(gzip.decompress(path.read_bytes())).iterfind("./courses/course")


def test_snapshot_matches_manifest() -> None:
    names = {f"{c.subject} {c.code}" for c in load_catalog(FIXTURE_DIR)}
    assert names == set(_manifest())


def test_snapshot_keeps_anchor_courses() -> None:
    assert set(ANCHORS) <= set(_manifest())


def test_snapshot_covers_every_quirk() -> None:
    tags: set[str] = set()
    for course in _courses():
        tags |= quirk_tags(course)
    # Cross-listing is a property of a group of courses, checked separately below.
    assert set(QUOTAS) - {"cross-listed"} <= tags


def test_snapshot_has_cross_listing_groups() -> None:
    listings_per_course_id = Counter(course_id(course) for course in _courses())
    groups = [cid for cid, n in listings_per_course_id.items() if cid and n > 1]
    assert len(groups) >= QUOTAS["cross-listed"]
