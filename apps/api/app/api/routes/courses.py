from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.course import Course
from app.schemas.course import CourseRead

router = APIRouter()


@router.get("", response_model=list[CourseRead])
def list_courses(
    session: Session = Depends(get_session),
    q: str | None = Query(None, description="Search by code, title, or department."),
    category: str | None = None,
    career_tag: str | None = None,
    term: str | None = None,
) -> list[Course]:
    stmt = select(Course)
    courses = list(session.exec(stmt).all())
    if q:
        ql = q.lower()
        courses = [
            c for c in courses
            if ql in c.code.lower() or ql in c.title.lower() or ql in c.department.lower()
        ]
    if category:
        courses = [c for c in courses if category in (c.categories or [])]
    if career_tag:
        courses = [c for c in courses if career_tag in (c.career_tags or [])]
    if term:
        courses = [c for c in courses if term in (c.offered_terms or [])]
    courses.sort(key=lambda c: c.code)
    return courses


@router.get("/{code}", response_model=CourseRead)
def get_course(code: str, session: Session = Depends(get_session)) -> Course:
    course = session.get(Course, code)
    if not course:
        raise HTTPException(404, f"Course '{code}' not found")
    return course
