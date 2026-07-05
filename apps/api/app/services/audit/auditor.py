"""Degree audit — deterministic.

Given a student and a program's requirements, compute per-requirement progress and
an overall report. This is intentionally pure-function: pass in the catalog and
the requirements list so it's trivial to test without a DB.
"""

from __future__ import annotations

from app.models.course import Course
from app.models.requirement import Requirement, RequirementType
from app.models.student import Student
from app.schemas.audit import AuditReport, RequirementProgress


def _credits_for(codes: list[str], catalog: dict[str, Course]) -> float:
    return sum(catalog[c].credits for c in codes if c in catalog)


def audit_requirement(
    req: Requirement,
    completed: set[str],
    catalog: dict[str, Course],
    creditable: set[str] | None = None,
) -> RequirementProgress:
    """`completed` satisfies course-based cards; `creditable` (defaults to
    `completed`) is the set whose credits count — waived courses satisfy
    cards but never earn credit."""
    if creditable is None:
        creditable = completed
    completed_in = [c for c in (req.courses or []) if c in completed]
    missing = [c for c in (req.courses or []) if c not in completed]

    satisfied = False
    progress_pct = 0.0
    notes = req.notes or ""

    if req.type == RequirementType.ALL_OF:
        satisfied = len(completed_in) == len(req.courses) and bool(req.courses)
        progress_pct = (len(completed_in) / len(req.courses)) if req.courses else 0.0
    elif req.type == RequirementType.ONE_OF:
        satisfied = len(completed_in) >= 1
        progress_pct = 1.0 if satisfied else 0.0
        if satisfied:
            # The untaken alternatives are not "missing" — the requirement is done.
            missing = []
    elif req.type == RequirementType.N_OF:
        need = max(req.count_required, 1)
        satisfied = len(completed_in) >= need
        progress_pct = min(len(completed_in) / need, 1.0)
        missing = [c for c in (req.courses or []) if c not in completed][: max(need - len(completed_in), 0)]
    elif req.type == RequirementType.CATEGORY_CREDITS:
        cat = req.category or ""
        matched = [c for c in creditable if cat in (catalog.get(c).categories if c in catalog else [])]
        earned = _credits_for(matched, catalog)
        satisfied = earned >= req.credits_required
        progress_pct = min(earned / req.credits_required, 1.0) if req.credits_required else 0.0
        return RequirementProgress(
            requirement_id=req.id or 0,
            name=req.name,
            type=str(req.type.value),
            satisfied=satisfied,
            progress_pct=round(progress_pct, 3),
            completed_courses=matched,
            missing_courses=[],
            needed_credits=max(req.credits_required - earned, 0.0),
            earned_credits=earned,
            notes=notes,
        )
    elif req.type == RequirementType.CREDITS:
        earned = _credits_for(list(creditable), catalog)
        satisfied = earned >= req.credits_required
        progress_pct = min(earned / req.credits_required, 1.0) if req.credits_required else 0.0
        return RequirementProgress(
            requirement_id=req.id or 0,
            name=req.name,
            type=str(req.type.value),
            satisfied=satisfied,
            progress_pct=round(progress_pct, 3),
            completed_courses=sorted(creditable),
            missing_courses=[],
            needed_credits=max(req.credits_required - earned, 0.0),
            earned_credits=earned,
            notes=notes,
        )

    if req.type == RequirementType.ONE_OF and not satisfied:
        # Only one option is needed — report the cheapest, not the sum of all.
        option_credits = [catalog[c].credits for c in missing if c in catalog]
        needed_credits = min(option_credits) if option_credits else 0.0
    else:
        needed_credits = _credits_for(missing, catalog)

    return RequirementProgress(
        requirement_id=req.id or 0,
        name=req.name,
        type=str(req.type.value),
        satisfied=satisfied,
        progress_pct=round(progress_pct, 3),
        completed_courses=completed_in,
        missing_courses=missing,
        needed_credits=needed_credits,
        earned_credits=_credits_for(completed_in, catalog),
        notes=notes,
    )


def audit_student(
    student: Student,
    program: str,
    requirements: list[Requirement],
    catalog: dict[str, Course],
) -> AuditReport:
    satisfying = student.satisfied_courses()
    creditable = set(student.completed_courses or [])
    progresses = [audit_requirement(r, satisfying, catalog, creditable) for r in requirements]

    total_credits_completed = _credits_for(list(creditable), catalog)
    total_credits_required = sum(r.credits_required for r in requirements) or 0.0
    completed_count = sum(1 for p in progresses if p.satisfied)
    overall = (
        sum(p.progress_pct for p in progresses) / len(progresses) if progresses else 0.0
    )

    blockers: list[str] = []
    warnings: list[str] = []
    if total_credits_required and total_credits_completed < 0.25 * total_credits_required:
        warnings.append("Less than 25% of credits completed — keep momentum on core courses.")
    unsatisfied_core = [p.name for p in progresses if not p.satisfied and p.type in {"all_of", "one_of"}]
    if len(unsatisfied_core) > 4:
        warnings.append(
            f"{len(unsatisfied_core)} core requirements still open — consider front-loading core courses."
        )

    return AuditReport(
        student_id=student.id or 0,
        program=program,
        requirements=progresses,
        total_credits_completed=round(total_credits_completed, 2),
        total_credits_required=round(total_credits_required, 2),
        overall_progress_pct=round(overall, 3),
        completed_count=completed_count,
        total_count=len(progresses),
        blockers=blockers,
        warnings=warnings,
    )
