from enum import Enum

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class RequirementType(str, Enum):
    ALL_OF = "all_of"  # student must take every course in `courses`
    ONE_OF = "one_of"  # at least one
    N_OF = "n_of"  # at least `count_required` from `courses`
    CATEGORY_CREDITS = "category_credits"  # credits_required from courses tagged with `category`
    CREDITS = "credits"  # total credits across whole program


class Requirement(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    program: str = Field(index=True)  # e.g. "columbia_cs_major"
    name: str
    type: RequirementType
    courses: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    category: str | None = None
    credits_required: float = 0.0
    count_required: int = 0
    display_order: int = 0
    notes: str = ""
