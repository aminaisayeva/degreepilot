from datetime import datetime

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Plan(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    name: str
    strategy: str  # "balanced" | "career_optimized" | "aggressive"
    terms: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    warnings: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    summary: dict = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
