from collections.abc import Iterator
from typing import Annotated

import psycopg
from fastapi import Depends, FastAPI, HTTPException

from api import queries
from api.models import CourseDetail, CourseSummary
from db.settings import db_settings

app = FastAPI(title="RedwoodSearch API")


def get_conn() -> Iterator[psycopg.Connection]:
    # One short-lived connection per request; plenty at pilot scale.
    with psycopg.connect(db_settings.database_url) as conn:
        yield conn


Conn = Annotated[psycopg.Connection, Depends(get_conn)]


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/courses")
def list_courses(conn: Conn) -> list[CourseSummary]:
    return queries.list_courses(conn)


@app.get("/api/courses/{subject}/{code}")
def get_course(subject: str, code: str, conn: Conn) -> CourseDetail:
    course = queries.get_course(conn, subject, code)
    if course is None:
        raise HTTPException(status_code=404, detail=f"No course {subject} {code}")
    return course
