from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.audit import AuditReport
from app.services.audit.auditor import audit_student

router = APIRouter()


def _catalog(session: Session) -> dict[str, Course]:
    return {c.code: c for c in session.exec(select(Course)).all()}


@router.get("/{student_id}/audit", response_model=AuditReport)
def get_student_audit(
    student_id: int,
    session: Session = Depends(get_session),
    program: str | None = Query(None),
) -> AuditReport:
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    if program is None:
        program = student.resolve_programs()[0]
    reqs = list(
        session.exec(
            select(Requirement)
            .where(Requirement.program == program)
            .order_by(Requirement.display_order)
        ).all()
    )
    if not reqs:
        raise HTTPException(404, f"No requirements defined for program '{program}'")
    return audit_student(student, program, reqs, _catalog(session))
