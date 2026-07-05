"""Plan validator — deterministic.

Validates a generated plan against the catalog, the student, and the program's
requirements. Returns a list of structured warnings.
"""

from __future__ import annotations

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.audit import AuditReport
from app.schemas.plan import PlanRead, PlanWarning, ValidationResult, SemesterPlan
from app.core.terms import parse_term
from app.services.audit.auditor import audit_student
from app.services.planner.prereq_graph import (
    assumed_completed,
    missing_prereqs,
    prereqs_satisfied,
)
from app.services.planner.scorers import workload_score_term


def validate_plan(
    plan: PlanRead,
    student: Student,
    catalog: dict[str, Course],
    requirements: list[Requirement],
    *,
    workload_ceiling: float = 16.0,
) -> ValidationResult:
    warnings: list[PlanWarning] = []
    seen: set[str] = student.satisfied_courses()
    duplicate_in_plan: set[str] = set()
    planned_so_far: set[str] = set()

    max_credits = max(student.max_credits_per_term, 12)
    last_term_idx = len(plan.terms) - 1

    for term_idx, term in enumerate(plan.terms):
        term_courses: list[Course] = [catalog[c] for c in term.courses if c in catalog]
        # duplicates within plan or against completed
        for code in term.courses:
            if code in duplicate_in_plan or code in seen:
                warnings.append(
                    PlanWarning(
                        severity="error",
                        code="duplicate_course",
                        message=f"{code} already taken or planned earlier.",
                        term=term.term,
                        course=code,
                    )
                )
            duplicate_in_plan.add(code)

        # term offering check
        try:
            season, _year = parse_term(term.term)
        except ValueError:
            season = None
            warnings.append(
                PlanWarning(
                    severity="error",
                    code="invalid_term",
                    message=f"Unrecognized term label {term.term!r} — expected e.g. 'Fall 2025'.",
                    term=term.term,
                )
            )
        for c in term_courses:
            if season and c.offered_terms and season not in c.offered_terms:
                warnings.append(
                    PlanWarning(
                        severity="warning",
                        code="not_offered_in_term",
                        message=f"{c.code} is typically not offered in {season}.",
                        term=term.term,
                        course=c.code,
                    )
                )

        # prereq check — completed + previously-planned courses count as satisfied
        # (plus waived undergrad prereqs for graduate students)
        completed_view = (
            student.satisfied_courses()
            | planned_so_far
            | assumed_completed(student.resolve_programs(), catalog)
        )
        for c in term_courses:
            if not prereqs_satisfied(c, completed_view):
                missing = missing_prereqs(c, completed_view)
                pretty = " AND ".join("(" + " OR ".join(g) + ")" for g in missing)
                warnings.append(
                    PlanWarning(
                        severity="error",
                        code="prereq_violation",
                        message=f"{c.code} prerequisites not met: {pretty}.",
                        term=term.term,
                        course=c.code,
                    )
                )

        # credit cap
        total_credits = sum(c.credits for c in term_courses)
        if total_credits > max_credits:
            warnings.append(
                PlanWarning(
                    severity="warning",
                    code="credit_overload",
                    message=f"{term.term}: {total_credits:g} credits exceeds your cap of {max_credits}.",
                    term=term.term,
                )
            )
        if total_credits < 12 and term_courses and term_idx != last_term_idx:
            warnings.append(
                PlanWarning(
                    severity="info",
                    code="part_time_load",
                    message=f"{term.term}: only {total_credits:g} credits — below full-time (12).",
                    term=term.term,
                )
            )

        # workload
        w_score = workload_score_term(term_courses)
        if w_score > workload_ceiling:
            warnings.append(
                PlanWarning(
                    severity="warning",
                    code="workload_overload",
                    message=f"{term.term}: workload score {w_score} is high — consider rebalancing.",
                    term=term.term,
                )
            )

        planned_so_far.update(term.courses)

    # Unmet graduation: simulate audit if every planned course were completed
    simulated = Student(**{**student.model_dump(), "completed_courses": list(seen | planned_so_far)})
    audit: AuditReport = audit_student(simulated, plan.summary.get("program", "columbia_cs_major"), requirements, catalog)
    if audit.completed_count < audit.total_count:
        unmet = [r.name for r in audit.requirements if not r.satisfied]
        warnings.append(
            PlanWarning(
                severity="error",
                code="unmet_graduation",
                message=f"Plan would leave {len(unmet)} requirement(s) unmet: {', '.join(unmet[:4])}"
                + ("…" if len(unmet) > 4 else ""),
            )
        )

    has_error = any(w.severity == "error" for w in warnings)
    return ValidationResult(is_valid=not has_error, warnings=warnings)


def annotate_term(term: SemesterPlan, catalog: dict[str, Course]) -> SemesterPlan:
    courses = [catalog[c] for c in term.courses if c in catalog]
    return SemesterPlan(
        term=term.term,
        courses=term.courses,
        total_credits=round(sum(c.credits for c in courses), 2),
        workload_score=workload_score_term(courses),
    )
