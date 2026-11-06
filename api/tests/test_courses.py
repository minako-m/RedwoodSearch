from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from api.main import app, get_conn
from ingest.load import load
from ingest.parse import load_listings

FIXTURE_DIR = Path(__file__).parents[2] / "ingest" / "fixtures" / "2026-2027"


@pytest.fixture(scope="module")
def client(migrated_db_url: str) -> Iterator[TestClient]:
    with psycopg.connect(migrated_db_url) as conn:
        load(conn, load_listings(FIXTURE_DIR))

    def test_conn() -> Iterator[psycopg.Connection]:
        with psycopg.connect(migrated_db_url) as conn:
            yield conn

    app.dependency_overrides[get_conn] = test_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_courses_in_catalog_order(client: TestClient) -> None:
    response = client.get("/api/courses")
    assert response.status_code == 200
    courses = response.json()
    assert len(courses) == 208
    cs = [c["code"] for c in courses if c["subject"] == "CS"]
    assert cs.index("106A") < cs.index("106B") < cs.index("107")
    cs106b = next(c for c in courses if c["subject"] == "CS" and c["code"] == "106B")
    assert cs106b["title"] == "Programming Abstractions"
    assert set(cs106b["terms"]) <= {"Autumn", "Winter", "Spring", "Summer"}


def test_course_detail(client: TestClient) -> None:
    response = client.get("/api/courses/CS/161")
    assert response.status_code == 200
    course = response.json()
    assert course["title"].startswith("Design and Analysis of Algorithms")
    assert course["prereq"]["status"] == "required"
    assert "CS 106B" in course["prereq"]["courses"]
    assert course["terms"], "CS 161 should be offered at least once"
    lectures = [s for t in course["terms"] for s in t["sections"] if s["component"] == "LEC"]
    meeting = lectures[0]["meetings"][0]
    assert meeting["days"] and meeting["start_minute"] < meeting["end_minute"]
    assert meeting["instructors"]


def test_course_detail_lists_cross_listings(client: TestClient) -> None:
    course = client.get("/api/courses/AFRICAAM/274").json()
    assert "AMSTUD 274" in course["cross_listings"]


def test_unknown_course_is_404(client: TestClient) -> None:
    assert client.get("/api/courses/CS/9999").status_code == 404
