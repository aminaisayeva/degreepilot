from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.terms import TERM_ORDER, format_term, parse_term


def _normalize_term(v: str | None) -> str | None:
    if v is None:
        return v
    season, year = parse_term(v)  # raises ValueError → 422 on bad input
    return format_term(season, year)


class StudentBase(BaseModel):
    name: str = "Anonymous Student"
    school: str = "Columbia University"
    major: str = "Computer Science"
    minor: str | None = None
    current_term: str = "Fall 2025"
    graduation_term: str = "Spring 2027"
    completed_courses: list[str] = Field(default_factory=list)
    waived_courses: list[str] = Field(default_factory=list)
    transfer_credits: list[dict] = Field(default_factory=list)
    preferred_workload: int = 3
    max_credits_per_term: int = 17
    career_goals: list[str] = Field(default_factory=list)
    constraints: dict = Field(default_factory=dict)
    programs: list[str] = Field(default_factory=list)

    _norm_terms = field_validator("current_term", "graduation_term")(_normalize_term)

    @model_validator(mode="after")
    def _graduation_not_before_start(self):
        cs, cy = parse_term(self.current_term)
        gs, gy = parse_term(self.graduation_term)
        if (gy, TERM_ORDER[gs]) < (cy, TERM_ORDER[cs]):
            raise ValueError(
                f"graduation_term ({self.graduation_term}) is before current_term ({self.current_term})"
            )
        return self


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    """Partial update — only fields the client sends are applied."""

    name: str | None = None
    school: str | None = None
    major: str | None = None
    minor: str | None = None
    current_term: str | None = None
    graduation_term: str | None = None
    completed_courses: list[str] | None = None
    waived_courses: list[str] | None = None
    transfer_credits: list[dict] | None = None
    preferred_workload: int | None = None
    max_credits_per_term: int | None = None
    career_goals: list[str] | None = None
    constraints: dict | None = None
    programs: list[str] | None = None

    _norm_terms = field_validator("current_term", "graduation_term")(_normalize_term)


class StudentRead(StudentBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
