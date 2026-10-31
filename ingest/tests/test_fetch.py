import urllib.parse

from ingest.fetch import department_url, parse_departments


def test_department_url_filters_to_offered_courses_in_year() -> None:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(department_url("CS", "2026-2027")).query)
    assert query["academicYear"] == ["20262027"]
    assert query["filter-departmentcode-CS"] == ["on"]
    for term in ("Autumn", "Winter", "Spring", "Summer"):
        assert query[f"filter-term-{term}"] == ["on"]


def test_department_url_escapes_ampersand() -> None:
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(department_url("MS&E", "2026-2027")).query)
    assert query["q"] == ["MS&E"]
    assert query["filter-departmentcode-MS&E"] == ["on"]


def test_parse_departments_dedupes_across_schools() -> None:
    xml = b"""<schools>
        <school name="A"><department name="CS" /><department name="MS&amp;E" /></school>
        <school name="B"><department name="CS" /></school>
    </schools>"""
    assert parse_departments(xml) == ["CS", "MS&E"]
