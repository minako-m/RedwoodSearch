from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from api.main import app, catalog
from ingest.parse import CourseSummary

COURSE = CourseSummary(
    subject="CS",
    code="106B",
    title="Programming Abstractions",
    units_min=3,
    units_max=5,
    gers=["WAY-FR"],
    terms=["Autumn"],
    career="UG",
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[catalog] = lambda: [COURSE]
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_list_courses_returns_catalog(client: TestClient) -> None:
    response = client.get("/api/courses")
    assert response.status_code == 200
    assert response.json() == [COURSE.model_dump()]
