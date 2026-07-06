from __future__ import annotations

from sqlmodel import Session, select

from app.core.db import engine
from app.models.course import Course
from app.models.requirement import Requirement
from app.seed.expand import add_prefix_variants, expand_dynamic_requirements, validate_catalog
from app.seed.loader import build_catalog
from app.seed.requirements import PROGRAMS


def seed_all(*, force: bool = False) -> dict:
    """Seed catalog and requirements.

    Courses: additive + field refresh — the merged catalog (snapshots +
    curated overlay) is authoritative, so existing rows are updated to match
    it. The merge itself guarantees curated fields win over scraped ones.
    Requirements: seed-owned — always replaced per program so list
    expansions reach existing databases.
    """
    catalog, _provenance = build_catalog()
    programs = expand_dynamic_requirements(PROGRAMS, catalog)
    programs = add_prefix_variants(programs, catalog)
    validate_catalog(catalog, programs)

    with Session(engine) as session:
        if force:
            for c in session.exec(select(Course)).all():
                session.delete(c)
            session.commit()

        existing = {c.code: c for c in session.exec(select(Course)).all()}
        for spec in catalog:
            row = existing.get(spec["code"])
            if row is None:
                session.add(Course(**spec))
                continue
            for field_name, value in spec.items():
                setattr(row, field_name, value)
            session.add(row)
        session.commit()

        # Prune requirements of programs no longer registered (e.g. disabled).
        for orphan in session.exec(select(Requirement)).all():
            if orphan.program not in programs:
                session.delete(orphan)
        session.commit()

        for program, reqs in programs.items():
            for old in session.exec(
                select(Requirement).where(Requirement.program == program)
            ).all():
                session.delete(old)
            for spec in reqs:
                session.add(Requirement(program=program, **spec))
        session.commit()

        return {
            "courses": len(session.exec(select(Course)).all()),
            "requirements": len(session.exec(select(Requirement)).all()),
        }
