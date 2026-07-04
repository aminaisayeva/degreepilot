from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.course import Course
from app.models.plan import Plan
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.plan import (
    GeneratePlanRequest,
    PlanCompareRequest,
    PlanCompareResult,
    PlanRead,
    PlanValidateRequest,
    ValidationResult,
)
from app.services.planner.comparator import compare_plans
from app.services.planner.generator import KNOWN_STRATEGIES, generate_plans
from app.services.planner.validator import validate_plan

router = APIRouter()


def _ctx(session: Session, programs: list[str]) -> tuple[dict[str, Course], list[Requirement]]:
    catalog = {c.code: c for c in session.exec(select(Course)).all()}
    reqs = list(
        session.exec(
            select(Requirement)
            .where(Requirement.program.in_(programs))  # type: ignore[attr-defined]
            .order_by(Requirement.display_order)
        ).all()
    )
    return catalog, reqs


@router.post("/generate", response_model=list[PlanRead])
def generate(payload: GeneratePlanRequest, session: Session = Depends(get_session)) -> list[PlanRead]:
    student = session.get(Student, payload.student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    unknown = [s for s in payload.strategies if s not in KNOWN_STRATEGIES]
    if unknown:
        raise HTTPException(422, f"Unknown strategies: {unknown}. Valid: {sorted(KNOWN_STRATEGIES)}")
    programs = student.resolve_programs()
    catalog, reqs = _ctx(session, programs)
    if not reqs:
        raise HTTPException(500, "Catalog/requirements not seeded.")
    plans = generate_plans(student, programs, reqs, catalog, strategies=payload.strategies)

    # Persist so the advisor can reference plans by id; replace prior generations.
    for old in session.exec(select(Plan).where(Plan.student_id == student.id)).all():
        session.delete(old)
    rows: list[Plan] = []
    for p in plans:
        row = Plan(
            student_id=student.id or 0,
            name=p.name,
            strategy=p.strategy,
            terms=[t.model_dump() for t in p.terms],
            warnings=[w.model_dump() for w in p.warnings],
            summary=p.summary,
        )
        session.add(row)
        rows.append(row)
    session.commit()
    for row, p in zip(rows, plans):
        session.refresh(row)
        p.id = row.id
        p.created_at = row.created_at
    return plans


@router.post("/validate", response_model=ValidationResult)
def validate(payload: PlanValidateRequest, session: Session = Depends(get_session)) -> ValidationResult:
    student = session.get(Student, payload.student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    catalog, reqs = _ctx(session, student.resolve_programs())
    return validate_plan(payload.plan, student, catalog, reqs)


@router.post("/compare", response_model=PlanCompareResult)
def compare(payload: PlanCompareRequest, session: Session = Depends(get_session)) -> PlanCompareResult:
    student = session.get(Student, payload.student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    catalog, reqs = _ctx(session, student.resolve_programs())
    return compare_plans(student, payload.plans, reqs, catalog)
