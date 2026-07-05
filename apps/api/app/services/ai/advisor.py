"""Deterministic advisor.

Pattern: classify the user's question into an intent, run the *real* deterministic
tool (audit / plan / validator), then ask the provider to phrase the answer.
The provider may be an LLM later — but the *facts* it uses come from the engine.
"""

from __future__ import annotations

import re

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.advisor import AdvisorRequest, AdvisorResponse, AdvisorToolCall
from app.schemas.plan import PlanRead
from app.services.ai.provider import DeterministicProvider, LLMProvider
from app.services.audit.auditor import audit_student
from app.services.planner.scorers import career_alignment_score
from app.services.planner.validator import validate_plan


INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("graduation_feasibility", re.compile(r"\b(graduate|on time|finish|done by)\b", re.I)),
    ("missing_requirements", re.compile(r"\b(missing|left|still need|remaining|requirement)\b", re.I)),
    ("study_abroad", re.compile(r"\b(abroad|exchange|study abroad)\b", re.I)),
    ("ai_ml_picks", re.compile(r"\b(ai|ml|machine learning|deep learning|nlp)\b", re.I)),
    ("recommendation_rationale", re.compile(r"\b(why.*(recommend|pick|chose|choose|suggested))\b", re.I)),
    ("plan_risk", re.compile(r"\b(risk|wrong|dangerous|red flag|blocker|concerns?)\b", re.I)),
]


def classify_intent(message: str) -> str:
    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(message):
            return intent
    return "general"


def _ml_picks(catalog: dict[str, Course], *, grad: bool = False) -> list[str]:
    cats = {"ms_track_ml", "grad_elective"} if grad else {"cs_track_ai", "cs_elective"}
    picks = [
        c for c in catalog.values()
        if any(t in {"ai_ml", "research"} for t in (c.career_tags or []))
        and any(cat in cats for cat in (c.categories or []))
    ]
    picks.sort(key=lambda c: (c.workload_level, c.code))
    return [c.code for c in picks[:5]]


def _study_abroad_blockers(plan: PlanRead | None, term: str | None) -> list[str]:
    if not plan or not term:
        return []
    target_term = next((t for t in plan.terms if t.term.lower() == term.lower()), None)
    return list(target_term.courses) if target_term else []


def _study_abroad_term_from_message(message: str) -> str | None:
    m = re.search(r"\b(Fall|Spring|Summer)\s*(20\d{2})\b", message, re.I)
    if m:
        return f"{m.group(1).capitalize()} {m.group(2)}"
    # rough mapping: "junior spring" -> a guess
    m2 = re.search(r"\b(freshman|sophomore|junior|senior)\s+(fall|spring)\b", message, re.I)
    if m2:
        return None  # advisor will ask which year if needed
    return None


def answer_advisor(
    request: AdvisorRequest,
    student: Student,
    catalog: dict[str, Course],
    requirements: list[Requirement],
    plan: PlanRead | None = None,
    provider: LLMProvider | None = None,
) -> AdvisorResponse:
    provider = provider or DeterministicProvider()
    intent = classify_intent(request.message)
    tool_calls: list[AdvisorToolCall] = []
    context: dict = {"graduation_term": student.graduation_term}

    if intent in {"graduation_feasibility", "missing_requirements", "general"}:
        # Run audit (and simulate plan if provided)
        sim_student = student
        if plan:
            placed = {c for t in plan.terms for c in t.courses}
            sim_student = Student(
                **{**student.model_dump(), "completed_courses": list(set(student.completed_courses) | placed)}
            )
        program_label = " + ".join(student.resolve_programs())
        audit = audit_student(sim_student, program_label, requirements, catalog)
        unmet = [r.name for r in audit.requirements if not r.satisfied]
        context["audit"] = audit.model_dump()
        context["unmet"] = unmet
        tool_calls.append(
            AdvisorToolCall(
                tool="audit_student",
                inputs={"student_id": student.id, "program": program_label, "with_plan": bool(plan)},
                output={"completed": audit.completed_count, "total": audit.total_count, "unmet": unmet},
            )
        )

    if intent == "study_abroad":
        term = _study_abroad_term_from_message(request.message)
        context["term"] = term or "the term you picked"
        blockers = _study_abroad_blockers(plan, term) if plan else []
        context["blockers"] = blockers
        tool_calls.append(
            AdvisorToolCall(
                tool="study_abroad_impact",
                inputs={"term": term},
                output={"blockers": blockers},
            )
        )

    if intent == "ai_ml_picks":
        grad = any(p.startswith(("columbia_ms", "columbia_ma_")) for p in student.resolve_programs())
        picks = _ml_picks(catalog, grad=grad)
        context["picks"] = picks
        tool_calls.append(
            AdvisorToolCall(
                tool="career_track_picks",
                inputs={"track": "ai_ml"},
                output={"picks": picks},
            )
        )

    if intent == "plan_risk" and plan:
        vr = validate_plan(plan, student, catalog, requirements)
        risks = [f"[{w.severity}] {w.message}" for w in vr.warnings]
        context["risks"] = risks
        tool_calls.append(
            AdvisorToolCall(
                tool="validate_plan",
                inputs={"plan_id": plan.id, "strategy": plan.strategy},
                output={"is_valid": vr.is_valid, "n_warnings": len(vr.warnings)},
            )
        )

    if intent == "recommendation_rationale" and plan:
        all_planned = [catalog[c] for t in plan.terms for c in t.courses if c in catalog]
        align = career_alignment_score(all_planned, student.career_goals)
        context["career_alignment"] = align
        tool_calls.append(
            AdvisorToolCall(
                tool="career_alignment_score",
                inputs={"plan_id": plan.id},
                output={"score": align},
            )
        )

    answer = provider.explain(intent, context)

    suggestions = []
    if intent == "graduation_feasibility":
        suggestions = [
            "Show me what's missing",
            "What if I study abroad junior spring?",
            "What are the risks in this plan?",
        ]
    elif intent == "missing_requirements":
        suggestions = [
            "Why did you recommend this plan?",
            "Best courses for AI/ML?",
            "Can I graduate on time?",
        ]

    return AdvisorResponse(
        intent=intent,
        answer=answer,
        tool_calls=tool_calls,
        citations=[f"DegreePilot/{c.tool}" for c in tool_calls],
        suggestions=suggestions,
    )
