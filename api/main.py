from functools import cache
from typing import Annotated

from fastapi import Depends, FastAPI

from api.settings import settings
from ingest.parse import CourseSummary, load_catalog

app = FastAPI(title="RedwoodSearch API")


@cache
def catalog() -> list[CourseSummary]:
    # Parsed once per process (~2 s for the full catalog). Replaced by DB queries in Step 2.
    return load_catalog(settings.raw_catalog_dir)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/courses")
def list_courses(courses: Annotated[list[CourseSummary], Depends(catalog)]) -> list[CourseSummary]:
    return courses
