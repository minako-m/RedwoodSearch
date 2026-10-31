import gzip
from pathlib import Path

from ingest.parse import load_catalog, parse_courses

COURSE_XML = b"""<xml><courses>
  <course>
    <subject>CS</subject><code>106B</code>
    <title> Programming Abstractions </title>
    <unitsMin>3</unitsMin><unitsMax>5</unitsMax>
    <gers>WAY-FR, GER:DB-EngrAppSci</gers>
    <administrativeInformation><academicCareer>UG</academicCareer></administrativeInformation>
    <sections>
      <section><term>2026-2027 Spring</term></section>
      <section><term>2026-2027 Autumn</term></section>
      <section><term>2026-2027 Autumn</term></section>
    </sections>
  </course>
</courses></xml>"""


def test_parse_courses_extracts_summary_fields() -> None:
    [course] = parse_courses(COURSE_XML)
    assert course.subject == "CS"
    assert course.code == "106B"
    assert course.title == "Programming Abstractions"
    assert (course.units_min, course.units_max) == (3, 5)
    assert course.gers == ["WAY-FR", "GER:DB-EngrAppSci"]
    assert course.terms == ["Autumn", "Spring"]
    assert course.career == "UG"


def test_parse_courses_handles_empty_fields() -> None:
    xml = b"<xml><courses><course><subject>X</subject><code>1</code><gers></gers></course>"
    [course] = parse_courses(xml + b"</courses></xml>")
    assert course.gers == []
    assert course.terms == []
    assert course.career is None


def _course(subject: str, code: str) -> bytes:
    return f"<course><subject>{subject}</subject><code>{code}</code></course>".encode()


def test_load_catalog_sorts_by_subject_then_number(tmp_path: Path) -> None:
    cs = b"<xml><courses>" + _course("CS", "106B") + _course("CS", "9") + _course("CS", "106A")
    (tmp_path / "CS.xml.gz").write_bytes(gzip.compress(cs + b"</courses></xml>"))
    aa = b"<xml><courses>" + _course("AA", "100") + b"</courses></xml>"
    (tmp_path / "AA.xml.gz").write_bytes(gzip.compress(aa))

    names = [f"{c.subject} {c.code}" for c in load_catalog(tmp_path)]
    assert names == ["AA 100", "CS 9", "CS 106A", "CS 106B"]
