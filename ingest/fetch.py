"""Download the ExploreCourses XML catalog for one academic year, one department at a time.

Only courses with at least one section in the given year are fetched: the term filters make the
server drop courses that are "not offered" that year.

Usage: uv run python -m ingest.fetch [--year 2026-2027] [--out data/raw]
"""

import argparse
import gzip
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

BASE_URL = "https://explorecourses.stanford.edu/"
XML_VIEW = "xml-20200810"
USER_AGENT = "RedwoodSearch/0.1 (+https://github.com/minako-m/RedwoodSearch)"
TERMS = ("Autumn", "Winter", "Spring", "Summer")
DELAY_SECONDS = 1.0
RETRIES = 3


def departments_url() -> str:
    return f"{BASE_URL}?view={XML_VIEW}"


def department_url(dept: str, year: str) -> str:
    """URL for every course in `dept` with a section in `year` (e.g. "2026-2027").

    `page=0` returns all results: in the XML view, `page=N` only skips the first 10*N courses.
    """
    params = [
        ("view", XML_VIEW),
        ("q", dept),
        ("filter-departmentcode-" + dept, "on"),
        ("filter-coursestatus-Active", "on"),
        ("academicYear", year.replace("-", "")),
        *[(f"filter-term-{term}", "on") for term in TERMS],
        ("page", "0"),
        ("collapse", ""),
    ]
    return f"{BASE_URL}search?{urllib.parse.urlencode(params)}"


def parse_departments(xml: bytes) -> list[str]:
    """Department codes in listing order, without duplicates (some appear under two schools)."""
    root = ET.fromstring(xml)
    codes = (d.get("name") for d in root.iter("department"))
    return list(dict.fromkeys(code for code in codes if code))


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, RETRIES + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                body: bytes = response.read()
            ET.fromstring(body)  # fail fast on truncated or non-XML responses
            return body
        except (OSError, ET.ParseError):
            if attempt == RETRIES:
                raise
            time.sleep(DELAY_SECONDS * 5 * attempt)
    raise AssertionError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--year", default="2026-2027")
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    out_dir: Path = args.out / args.year
    out_dir.mkdir(parents=True, exist_ok=True)

    listing = get(departments_url())
    (out_dir / "departments.xml").write_bytes(listing)
    departments = parse_departments(listing)

    for i, dept in enumerate(departments, 1):
        path = out_dir / f"{dept.replace('&', 'and')}.xml.gz"
        if path.exists():  # resumable: skip departments already downloaded
            continue
        time.sleep(DELAY_SECONDS)
        body = get(department_url(dept, args.year))
        path.write_bytes(gzip.compress(body))
        print(f"[{i}/{len(departments)}] {dept}: {len(body) / 1e6:.1f} MB", flush=True)


if __name__ == "__main__":
    main()
