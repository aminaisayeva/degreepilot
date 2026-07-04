from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.directory_sync import DirectorySync
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
