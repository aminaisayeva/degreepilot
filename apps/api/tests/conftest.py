from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.seed.courses import CS_AND_ECON_COURSES
from app.seed.requirements import PROGRAMS


@pytest.fixture
def engine_mem():
    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(eng)
    return eng


@pytest.fixture
def session(engine_mem):
    with Session(engine_mem) as s:
        for spec in CS_AND_ECON_COURSES:
            s.add(Course(**spec))
        for program, reqs in PROGRAMS.items():
            for spec in reqs:
                s.add(Requirement(program=program, **spec))
        s.commit()
        yield s


@pytest.fixture
def catalog(session):
    from sqlmodel import select

    return {c.code: c for c in session.exec(select(Course)).all()}


@pytest.fixture
def cs_reqs(session):
    from sqlmodel import select

    return list(
        session.exec(
            select(Requirement)
            .where(Requirement.program == "columbia_cs_major")
            .order_by(Requirement.display_order)
        ).all()
    )


@pytest.fixture
def fresh_student():
    return Student(
        id=1,
        name="Test Student",
        completed_courses=[],
        current_term="Fall 2025",
        graduation_term="Spring 2028",
        career_goals=["ai_ml"],
        preferred_workload=3,
        max_credits_per_term=17,
    )


@pytest.fixture
def midway_student():
    return Student(
        id=2,
        name="Junior Student",
        completed_courses=[
            "COMS W1004",
            "COMS W3134",
            "COMS W3203",
            "MATH UN1101",
            "MATH UN1201",
            "ECON UN1105",
        ],
        current_term="Fall 2025",
        graduation_term="Spring 2028",
        career_goals=["ai_ml", "quant"],
        preferred_workload=3,
        max_credits_per_term=17,
    )


@pytest.fixture
def ms_reqs(session):
    from sqlmodel import select

    return list(
        session.exec(
            select(Requirement)
            .where(Requirement.program == "columbia_ms_cs")
            .order_by(Requirement.display_order)
        ).all()
    )


@pytest.fixture
def ms_student():
    return Student(
        id=3,
        name="MS Test Student",
        major="Computer Science (MS)",
        completed_courses=[],
        current_term="Fall 2025",
        graduation_term="Spring 2027",
        career_goals=["ai_ml"],
        preferred_workload=4,
        max_credits_per_term=12,
        programs=["columbia_ms_cs"],
    )
