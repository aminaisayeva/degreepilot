from pydantic import BaseModel


class RequirementProgress(BaseModel):
    requirement_id: int
    name: str
    type: str
    satisfied: bool
    progress_pct: float
    completed_courses: list[str]
    missing_courses: list[str]
    needed_credits: float = 0.0
    earned_credits: float = 0.0
    notes: str = ""


class AuditReport(BaseModel):
    student_id: int
    program: str
    requirements: list[RequirementProgress]
    total_credits_completed: float
    total_credits_required: float
    overall_progress_pct: float
    completed_count: int
    total_count: int
    blockers: list[str]
    warnings: list[str]
