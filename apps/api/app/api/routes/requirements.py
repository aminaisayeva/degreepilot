from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.requirement import Requirement
from app.schemas.requirement import RequirementRead
from app.seed.requirements import PROGRAM_LABELS

router = APIRouter()


@router.get("", response_model=list[dict])
def list_programs(session: Session = Depends(get_session)) -> list[dict]:
    """Return every program slug we have requirements for, with friendly labels."""
    slugs = sorted({r.program for r in session.exec(select(Requirement)).all()})
    return [{"slug": s, "label": PROGRAM_LABELS.get(s, s)} for s in slugs]


@router.get("/{program}", response_model=list[RequirementRead])
def list_requirements(program: str, session: Session = Depends(get_session)) -> list[Requirement]:
    stmt = select(Requirement).where(Requirement.program == program).order_by(Requirement.display_order)
    reqs = list(session.exec(stmt).all())
    if not reqs:
        raise HTTPException(404, f"No requirements defined for program '{program}'")
    return reqs
