"""A pre-built demo student so the app has something live on first boot.

The course codes here mirror the Columbia College bulletin format.
"""

from __future__ import annotations

from sqlmodel import Session, select

from app.core.db import engine
from app.models.student import Student


DEMO = {
    "name": "Alex Demo",
    "school": "Columbia University",
    "major": "Computer Science",
    "minor": "Economics",
    "current_term": "Fall 2025",
    "graduation_term": "Spring 2028",
    # A realistic sophomore-going-into-junior: started intro CS, knocked out
    # part of the Core (Lit Hum sequence, University Writing, Frontiers, one
    # PE), two terms of calc, and Principles of Econ.
    "completed_courses": [
        # Core
        "ENGL CC1010",
        "SCNC CC1000",
        "HUMA CC1001",
        "HUMA CC1002",
        "PHED UN1001",
        # CS / Math
        "COMS W1004",
        "COMS W3134",
        "COMS W3203",
        "MATH UN1101",
        "MATH UN1201",
        # Econ
        "ECON UN1105",
    ],
    "transfer_credits": [],
    "preferred_workload": 3,
    "max_credits_per_term": 17,
    "career_goals": ["ai_ml", "quant"],
    "constraints": {"no_summer": True, "study_abroad_term": None},
    "programs": ["columbia_cc_core", "columbia_cs_major", "columbia_econ_concentration"],
}

# A graduate demo: first-year MS in CS, one semester in.
DEMO_MS = {
    "name": "Maya Demo",
    "school": "Columbia University",
    "major": "Computer Science (MS)",
    "minor": None,
    "current_term": "Spring 2026",
    "graduation_term": "Spring 2027",
    "completed_courses": [
        "COMS W4118",  # Breadth: Systems
        "COMS W4771",  # Breadth: AI & Applications
        "COMS E6893",  # Track depth (ML)
    ],
    "transfer_credits": [],
    "preferred_workload": 4,
    "max_credits_per_term": 12,
    "career_goals": ["ai_ml", "data"],
    "constraints": {"no_summer": True, "study_abroad_term": None},
    "programs": ["columbia_ms_cs"],
}


def ensure_demo_student() -> int:
    with Session(engine) as session:
        first_id: int | None = None
        for spec in (DEMO, DEMO_MS):
            existing = session.exec(select(Student).where(Student.name == spec["name"])).first()
            if existing:
                sid = existing.id
            else:
                s = Student(**spec)
                session.add(s)
                session.commit()
                session.refresh(s)
                sid = s.id
            if first_id is None:
                first_id = sid
        return first_id  # type: ignore[return-value]
