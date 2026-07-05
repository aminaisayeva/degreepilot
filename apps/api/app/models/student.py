from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Student(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = "Anonymous Student"
    school: str = "Columbia University"
    major: str = "Computer Science"
    minor: str | None = None
    current_term: str = "Fall 2025"
    graduation_term: str = "Spring 2027"
    completed_courses: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    # Courses counted toward a PRIOR degree (e.g. bachelor's): they waive the
    # matching requirement but earn NO credit toward this degree — other
    # courses must fill the points (cs.columbia.edu MS waiver policy).
    waived_courses: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    transfer_credits: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    preferred_workload: int = 3
    max_credits_per_term: int = 17
    career_goals: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    constraints: dict = Field(default_factory=dict, sa_column=Column(JSON))
    programs: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def satisfied_courses(self) -> set[str]:
        """Courses that satisfy requirements and prerequisites: actually
        completed plus waived. Credit math must use `completed_courses` only."""
        return set(self.completed_courses or []) | set(self.waived_courses or [])

    def resolve_programs(self) -> list[str]:
        """Programs this student plans/audits against.

        Falls back to the undergrad CS default for records created before
        the `programs` field existed.
        """
        if self.programs:
            return list(self.programs)
        progs = ["columbia_cc_core", "columbia_cs_major"]
        if (self.minor or "").strip().lower() == "economics":
            progs.append("columbia_econ_concentration")
        return progs
