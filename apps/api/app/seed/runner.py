from __future__ import annotations

from sqlmodel import Session, select

from app.core.db import engine
from app.models.course import Course
from app.models.requirement import Requirement
from app.seed.courses import CS_AND_ECON_COURSES
from app.seed.requirements import PROGRAMS


def seed_all(*, force: bool = False) -> dict:
    """Seed catalog and requirements.

    Additive-idempotent: courses and programs added in newer versions are
    inserted into existing databases; already-seeded rows are left untouched.
    force=True wipes and reseeds everything.
    """
    with Session(engine) as session:
        if force:
            for c in session.exec(select(Course)).all():
                session.delete(c)
            for r in session.exec(select(Requirement)).all():
                session.delete(r)
            session.commit()

        existing_codes = {c.code for c in session.exec(select(Course)).all()}
        for spec in CS_AND_ECON_COURSES:
            if spec["code"] not in existing_codes:
                session.add(Course(**spec))
        session.commit()

        existing_programs = {r.program for r in session.exec(select(Requirement)).all()}
        for program, reqs in PROGRAMS.items():
            if program not in existing_programs:
                for spec in reqs:
                    session.add(Requirement(program=program, **spec))
        session.commit()

        return {
            "courses": session.exec(select(Course)).all().__len__(),
            "requirements": session.exec(select(Requirement)).all().__len__(),
        }
