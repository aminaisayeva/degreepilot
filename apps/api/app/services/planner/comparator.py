"""Plan comparison — side-by-side metrics + a recommended winner."""

from __future__ import annotations

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.audit import AuditReport
from app.schemas.plan import PlanCompareResult, PlanRead
from app.services.audit.auditor import audit_student


def _summarize(plan: PlanRead) -> dict:
    s = dict(plan.summary or {})
    s["name"] = plan.name
    s["strategy"] = plan.strategy
    s["num_warnings"] = len(plan.warnings)
    s["num_errors"] = sum(1 for w in plan.warnings if w.severity == "error")
    s["num_terms"] = len(plan.terms)
    s["max_workload"] = max((t.workload_score for t in plan.terms), default=0.0)
    s["min_workload"] = min((t.workload_score for t in plan.terms), default=0.0)
    return s


def compare_plans(
    student: Student,
    plans: list[PlanRead],
    requirements: list[Requirement],
    catalog: dict[str, Course],
) -> PlanCompareResult:
    if not plans:
        return PlanCompareResult(
            plans=[], summaries=[], winner=None, rationale="No plans to compare.", audits=[]
        )
    summaries = [_summarize(p) for p in plans]
    audits: list[AuditReport] = []
    for p in plans:
        placed = {c for t in p.terms for c in t.courses}
        sim = Student(
            **{**student.model_dump(), "completed_courses": list(set(student.completed_courses or []) | placed)}
        )
        audits.append(audit_student(sim, p.summary.get("program", "columbia_cs_major"), requirements, catalog))

    # Winner heuristic:
    #   - zero errors required
    #   - more completed reqs > higher career alignment > lower workload variance > fewer terms
    rankable = list(zip(plans, summaries, audits))

    def key(t):
        plan, summary, audit = t
        return (
            summary["num_errors"],  # lower better
            -audit.completed_count,  # higher better
            -summary.get("career_alignment", 0.0),  # higher better
            summary.get("workload_variance", 0.0),  # lower better
            summary["num_terms"],  # fewer better
        )

    rankable.sort(key=key)
    winner_plan, _, _ = rankable[0]

    rationale_parts = []
    if winner_plan.summary.get("career_alignment", 0):
        rationale_parts.append(
            f"highest career alignment ({winner_plan.summary['career_alignment']:.0%})"
        )
    rationale_parts.append(f"{len(winner_plan.terms)} terms")
    if winner_plan.warnings:
        errs = [w for w in winner_plan.warnings if w.severity == "error"]
        if errs:
            rationale_parts.append(f"{len(errs)} hard blockers")
        else:
            rationale_parts.append("no hard blockers")
    rationale = (
        f"{winner_plan.name} wins on: " + ", ".join(rationale_parts) + "."
    )

    return PlanCompareResult(
        plans=plans,
        summaries=summaries,
        winner=winner_plan.name,
        rationale=rationale,
        audits=audits,
    )
