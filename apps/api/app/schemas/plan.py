from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.audit import AuditReport


class SemesterPlan(BaseModel):
    term: str  # e.g. "Fall 2025"
    courses: list[str] = Field(default_factory=list)
    total_credits: float = 0.0
    workload_score: float = 0.0


class PlanWarning(BaseModel):
    severity: str  # "info" | "warning" | "error"
    code: str  # machine-readable, e.g. "prereq_violation"
    message: str
    term: str | None = None
    course: str | None = None


class PlanRead(BaseModel):
    id: int | None = None
    student_id: int
    name: str
    strategy: str
    terms: list[SemesterPlan]
    warnings: list[PlanWarning] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class GeneratePlanRequest(BaseModel):
    student_id: int
    strategies: list[str] = Field(default_factory=lambda: ["balanced", "career_optimized"])


class PlanValidateRequest(BaseModel):
    student_id: int
    plan: PlanRead


class ValidationResult(BaseModel):
    is_valid: bool
    warnings: list[PlanWarning]


class PlanCompareRequest(BaseModel):
    student_id: int
    plans: list[PlanRead]


class PlanCompareResult(BaseModel):
    plans: list[PlanRead]
    summaries: list[dict]
    winner: str | None = None
    rationale: str = ""
    audits: list[AuditReport] = Field(default_factory=list)
