from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.accuracy import AccuracyCheck
from app.models.course import Course
from app.models.directory_sync import DirectorySync
from app.models.requirement import Requirement
from app.services.accuracy import build_accuracy_data
from app.services.sync.syncer import DEFAULT_SUBJECTS, sync_many, sync_subject_term

router = APIRouter()


@router.post("/sync")
def trigger_sync(
    background: BackgroundTasks,
    term: str = Query("Fall2026", description="Columbia URL term form, e.g. Fall2026"),
    subjects: list[str] | None = Query(
        None, description="Subject codes to sync. Defaults to COMS, CSEE, ECON, MATH, STAT, IEOR.",
    ),
    wait: bool = Query(False, description="Run sync in foreground and return results."),
    session: Session = Depends(get_session),
) -> dict:
    """Trigger a sync of the Columbia Directory of Classes."""
    targets = subjects or list(DEFAULT_SUBJECTS)
    if wait:
        records = sync_many(targets, term=term, session=session)
        return {
            "term": term,
            "subjects": targets,
            "results": [_dump(r) for r in records],
        }
    background.add_task(_background_sync, targets, term)
    return {"term": term, "subjects": targets, "queued": True}


def _background_sync(targets: list[str], term: str) -> None:
    from app.core.db import engine
    from sqlmodel import Session as _S

    with _S(engine) as s:
        for subject in targets:
            sync_subject_term(subject, term, session=s)


@router.get("/sync/status", response_model=list[dict])
def sync_status(
    session: Session = Depends(get_session),
    limit: int = 20,
) -> list[dict]:
    rows = list(
        session.exec(select(DirectorySync).order_by(DirectorySync.fetched_at.desc())).all()
    )
    return [_dump(r) for r in rows[:limit]]


_STATIC = Path(__file__).resolve().parents[2] / "static"


@router.get("/accuracy", response_class=HTMLResponse)
def accuracy_page() -> HTMLResponse:
    return HTMLResponse((_STATIC / "accuracy.html").read_text())


class CheckIn(BaseModel):
    entity_type: str
    entity_key: str
    status: str
    notes: str = ""


@router.get("/accuracy/data")
def accuracy_data(session: Session = Depends(get_session)) -> dict:
    return build_accuracy_data(session)


@router.post("/accuracy/check")
def upsert_check(body: CheckIn, session: Session = Depends(get_session)) -> dict:
    if body.entity_type not in ("course", "requirement"):
        raise HTTPException(422, "entity_type must be 'course' or 'requirement'")
    if body.status not in ("verified", "incorrect", "unchecked"):
        raise HTTPException(422, "status must be verified | incorrect | unchecked")

    if body.entity_type == "course":
        if not session.get(Course, body.entity_key):
            raise HTTPException(404, f"Course '{body.entity_key}' not found")
    else:
        program, _, name = body.entity_key.partition("/")
        row = session.exec(
            select(Requirement)
            .where(Requirement.program == program)
            .where(Requirement.name == name)
        ).first()
        if not row:
            raise HTTPException(404, f"Requirement '{body.entity_key}' not found")

    existing = session.exec(
        select(AccuracyCheck)
        .where(AccuracyCheck.entity_type == body.entity_type)
        .where(AccuracyCheck.entity_key == body.entity_key)
    ).first()

    if body.status == "unchecked":
        if existing:
            session.delete(existing)
            session.commit()
        return {"entity_type": body.entity_type, "entity_key": body.entity_key,
                "status": "unchecked"}

    if existing:
        existing.status = body.status
        existing.notes = body.notes
        existing.checked_at = datetime.utcnow()
        session.add(existing)
    else:
        existing = AccuracyCheck(entity_type=body.entity_type, entity_key=body.entity_key,
                                 status=body.status, notes=body.notes)
        session.add(existing)
    session.commit()
    session.refresh(existing)
    return {"entity_type": existing.entity_type, "entity_key": existing.entity_key,
            "status": existing.status, "notes": existing.notes,
            "checked_at": existing.checked_at.isoformat() + "Z"}


def _dump(r: DirectorySync) -> dict:
    return {
        "id": r.id,
        "subject": r.subject,
        "term": r.term,
        "fetched_at": r.fetched_at.isoformat() + "Z",
        "status": r.status,
        "courses_fetched": r.courses_fetched,
        "courses_inserted": r.courses_inserted,
        "courses_updated": r.courses_updated,
        "error": r.error,
    }
