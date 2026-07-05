"""Build the accuracy-dashboard payload: programs → requirements → courses,
joined with human verification checks and scrape provenance."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from sqlmodel import Session, select

from app.models.accuracy import AccuracyCheck
from app.models.course import Course
from app.models.requirement import Requirement
from app.seed.requirements import PROGRAM_LABELS

_DIRECTORY_URL = "https://doc.sis.columbia.edu/subj/{subject}/_{term}.html"


@lru_cache(maxsize=1)
def _provenance() -> dict[str, dict]:
    """Provenance comes from the committed snapshot files — static per
    process, so cache it."""
    from app.seed.loader import build_catalog

    _courses, provenance = build_catalog()
    return provenance


@lru_cache(maxsize=1)
def _policies() -> list[dict]:
    """Q/A entries scraped from the MS FAQ pages — static per process."""
    import json

    from app.seed.loader import DATA_DIR

    path = DATA_DIR / "ms_faq.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    out: list[dict] = []
    for page in (payload.get("pages") or {}).values():
        for e in page.get("entries") or []:
            out.append({**e, "source_url": page.get("source_url")})
    return out


@lru_cache(maxsize=1)
def _newest_directory_term() -> str:
    from app.seed.loader import DATA_DIR

    def sort_key(name: str) -> tuple[int, int]:
        term = name.removeprefix("directory_").removesuffix(".json")
        season = 0 if term.startswith("Spring") else (1 if term.startswith("Summer") else 2)
        year = int("".join(ch for ch in term if ch.isdigit()) or 0)
        return (year, season)

    names = [p.name for p in DATA_DIR.glob("directory_*.json")]
    if not names:
        return "Fall2026"
    newest = max(names, key=sort_key)
    return newest.removeprefix("directory_").removesuffix(".json")


def _course_row(code: str, course: Course | None, prov: dict[str, dict],
                checks: dict, term: str) -> dict:
    p = prov.get(code, {})
    row = {
        "code": code,
        "in_catalog": course is not None,
        "origin": p.get("origin", "curated" if course else "missing"),
        "source_url": p.get("source_url"),
        "scraped_at": p.get("scraped_at"),
        "bulletin_prereq_text": p.get("bulletin_prereq_text", ""),
        "directory_url": _DIRECTORY_URL.format(subject=code.split()[0], term=term),
        "check": checks.get(("course", code)),
    }
    if course is not None:
        row.update({
            "title": course.title,
            "credits": course.credits,
            "offered_terms": course.offered_terms or [],
            "prerequisites": course.prerequisites or [],
            "categories": course.categories or [],
        })
    else:
        row.update({"title": None, "credits": None, "offered_terms": [],
                    "prerequisites": [], "categories": []})
    return row


def build_accuracy_data(session: Session) -> dict:
    prov = _provenance()
    term = _newest_directory_term()

    courses = {c.code: c for c in session.exec(select(Course)).all()}
    checks: dict[tuple[str, str], dict] = {}
    for chk in session.exec(select(AccuracyCheck)).all():
        checks[(chk.entity_type, chk.entity_key)] = {
            "status": chk.status,
            "notes": chk.notes,
            "checked_at": chk.checked_at.isoformat() + "Z",
        }

    programs_out: list[dict] = []
    summary: dict[str, dict] = {}
    for slug, label in PROGRAM_LABELS.items():
        reqs = list(session.exec(
            select(Requirement)
            .where(Requirement.program == slug)
            .order_by(Requirement.display_order)
        ).all())
        req_rows: list[dict] = []
        total = verified = incorrect = 0
        for req in reqs:
            entity_key = f"{slug}/{req.name}"
            req_check = checks.get(("requirement", entity_key))
            course_rows = [
                _course_row(code, courses.get(code), prov, checks, term)
                for code in (req.courses or [])
            ]
            for row in [{"check": req_check}, *course_rows]:
                total += 1
                status = (row.get("check") or {}).get("status")
                if status == "verified":
                    verified += 1
                elif status == "incorrect":
                    incorrect += 1
            req_rows.append({
                "name": req.name,
                "entity_key": entity_key,
                "type": req.type.value if hasattr(req.type, "value") else req.type,
                "count_required": req.count_required,
                "credits_required": req.credits_required,
                "notes": req.notes,
                "check": req_check,
                "courses": course_rows,
            })
        programs_out.append({"slug": slug, "label": label, "requirements": req_rows})
        summary[slug] = {"total": total, "verified": verified, "incorrect": incorrect}

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "programs": programs_out,
        "catalog_size": len(courses),
        "summary": summary,
        "policies": _policies(),
    }
