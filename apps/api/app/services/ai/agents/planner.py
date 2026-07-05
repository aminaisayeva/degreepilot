"""Planner agent — proposes a candidate answer.

In v1 the Planner is mostly deterministic — it calls the existing planner
services (career_track_picks, study_abroad_impact, etc.). In v1.1 the
Planner is the natural place to wire a real LLM, because phrasing
substitution suggestions ("swap COMS W4118 to Spring 2027") is the
operation that benefits most from natural-language flexibility.

On retry, the Planner sees `scratchpad.critic_verdict.violations` and is
expected to propose a different candidate.
"""

from __future__ import annotations

import time

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.plan import PlanRead
from app.services.ai.agents.scratchpad import AdvisorScratchpad
from app.services.planner.validator import validate_plan


class Planner:
    name = "Planner"

    def __init__(
        self,
        student: Student,
        catalog: dict[str, Course],
        requirements: list[Requirement],
        plan: PlanRead | None = None,
    ) -> None:
        self.student = student
        self.catalog = catalog
        self.requirements = requirements
        self.plan = plan

    def run(self, scratchpad: AdvisorScratchpad) -> None:
        started = time.perf_counter()
        intent = scratchpad.intent or "general"

        if intent == "ai_ml_picks":
            self._do_ai_ml_picks(scratchpad)
        elif intent == "study_abroad":
            self._do_study_abroad(scratchpad)
        elif intent == "plan_risk":
            self._do_plan_risk(scratchpad)
        elif intent == "recommendation_rationale":
            self._do_rationale(scratchpad)
        else:
            # Info-only intents (graduation_feasibility, missing_requirements, general)
            # don't need the Planner to propose anything beyond what the Researcher
            # already supplied.
            scratchpad.add_trace(
                agent=self.name,
                action="no_op",
                status="ok",
                summary=f"no proposal needed for intent={intent}",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )
            return

        scratchpad.add_trace(
            agent=self.name,
            action=intent,
            status="ok",
            summary=self._summary_for(intent, scratchpad),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ----- per-intent actions -----

    def _do_ai_ml_picks(self, scratchpad: AdvisorScratchpad) -> None:
        grad = any(p.startswith(("columbia_ms", "columbia_ma_")) for p in self.student.resolve_programs())
        cats = {"ms_track_ml", "grad_elective"} if grad else {"cs_track_ai", "cs_area_foundation"}
        picks = [
            c.code
            for c in self.catalog.values()
            if any(t in {"ai_ml", "research"} for t in (c.career_tags or []))
            and any(cat in cats for cat in (c.categories or []))
        ]
        picks.sort(key=lambda code: (self.catalog[code].workload_level, code))
        picks = picks[:5]
        scratchpad.add_tool_call(
            tool="career_track_picks",
            inputs={"track": "ai_ml"},
            output={"picks": picks},
        )
        scratchpad.context["picks"] = picks

    def _do_study_abroad(self, scratchpad: AdvisorScratchpad) -> None:
        term = self._extract_term(scratchpad.user_message)
        blockers: list[str] = []
        if self.plan and term:
            for t in self.plan.terms:
                if t.term.lower() == term.lower():
                    blockers = list(t.courses)
                    break
        scratchpad.add_tool_call(
            tool="study_abroad_impact",
            inputs={"term": term},
            output={"blockers": blockers},
        )
        # "term" is the key the explanation provider reads.
        scratchpad.context["term"] = term or "the term you picked"
        scratchpad.context["study_abroad_term"] = term or "the term you picked"
        scratchpad.context["blockers"] = blockers

    def _do_plan_risk(self, scratchpad: AdvisorScratchpad) -> None:
        if self.plan is None:
            scratchpad.context["risks"] = []
            return
        result = validate_plan(self.plan, self.student, self.catalog, self.requirements)
        risks = [f"[{w.severity}] {w.message}" for w in result.warnings]
        scratchpad.add_tool_call(
            tool="validate_plan",
            inputs={"plan_id": self.plan.id, "strategy": self.plan.strategy},
            output={"is_valid": result.is_valid, "n_warnings": len(result.warnings)},
        )
        scratchpad.context["risks"] = risks

    def _do_rationale(self, scratchpad: AdvisorScratchpad) -> None:
        if self.plan is None:
            return
        scratchpad.context["plan_name"] = self.plan.name
        align = self.plan.summary.get("career_alignment", 0.0) if self.plan.summary else 0.0
        scratchpad.context["career_alignment"] = align
        scratchpad.add_tool_call(
            tool="career_alignment_score",
            inputs={"plan_id": self.plan.id},
            output={"score": align},
        )

    # ----- helpers -----

    @staticmethod
    def _extract_term(message: str) -> str | None:
        import re

        m = re.search(r"\b(Fall|Spring|Summer)\s*(20\d{2})\b", message, re.I)
        if m:
            return f"{m.group(1).capitalize()} {m.group(2)}"
        return None

    def _summary_for(self, intent: str, scratchpad: AdvisorScratchpad) -> str:
        if intent == "ai_ml_picks":
            picks = scratchpad.context.get("picks") or []
            return f"picked {len(picks)} AI/ML courses"
        if intent == "study_abroad":
            blockers = scratchpad.context.get("blockers") or []
            return f"{len(blockers)} blocker(s) in {scratchpad.context.get('study_abroad_term')}"
        if intent == "plan_risk":
            risks = scratchpad.context.get("risks") or []
            return f"{len(risks)} risk(s) flagged"
        if intent == "recommendation_rationale":
            return f"alignment={scratchpad.context.get('career_alignment', 0)}"
        return ""
