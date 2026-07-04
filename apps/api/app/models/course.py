from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Course(SQLModel, table=True):
    """A single university course.

    `prerequisites` is stored as a CNF-style list of OR-groups:
      [["COMS W3134"], ["COMS W3203", "MATH UN2010"]]
    means: COMS W3134 AND (COMS W3203 OR MATH UN2010).
    """

    code: str = Field(primary_key=True, index=True)
    title: str
    department: str
    credits: float = 3.0
    description: str = ""
    workload_level: int = 3  # 1=light, 5=brutal
    offered_terms: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    prerequisites: list[list[str]] = Field(default_factory=list, sa_column=Column(JSON))
    categories: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    career_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
