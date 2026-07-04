"""Researcher agent — gathers deterministic context from the existing services.

Read-only. Calls audit + catalog + (optional) plan to populate `scratchpad.context`.
Does not propose answers.
"""

from __future__ import annotations

import time

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.plan import PlanRead
from app.services.ai.agents.scratchpad import AdvisorScratchpad
from app.services.audit.auditor import audit_student


class Researcher:
    name = "Researcher"

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

    def _program_label(self) -> str:
        return " + ".join(self.student.resolve_programs())

    def run(self, scratchpad: AdvisorScratchpad) -> None:
        started = time.perf_counter()

        scratchpad.context["graduation_term"] = self.student.graduation_term
        scratchpad.context["current_term"] = self.student.current_term
        scratchpad.context["career_goals"] = list(self.student.career_goals or [])
        scratchpad.context["completed_courses"] = list(self.student.completed_courses or [])
        scratchpad.context["known_course_codes"] = sorted(self.catalog.keys())

        if self.plan is not None:
            scratchpad.context["has_plan"] = True
            scratchpad.context["plan_strategy"] = self.plan.strategy
            scratchpad.context["plan_terms"] = [
                {"term": t.term, "courses": list(t.courses)} for t in self.plan.terms
            ]
            # Simulate audit with the plan applied so the Critic + Explainer can reason about it.
            placed = {c for t in self.plan.terms for c in t.courses}
            sim_student = Student(
                **{
                    **self.student.model_dump(),
                    "completed_courses": list(set(self.student.completed_courses or []) | placed),
                }
            )
            audit = audit_student(sim_student, self._program_label(), self.requirements, self.catalog)
        else:
            scratchpad.context["has_plan"] = False
            audit = audit_student(
                self.student, self._program_label(), self.requirements, self.catalog
            )

        unmet = [r.name for r in audit.requirements if not r.satisfied]
        scratchpad.context["audit"] = {
            "completed_count": audit.completed_count,
            "total_count": audit.total_count,
            "overall_progress_pct": audit.overall_progress_pct,
            "unmet": unmet,
        }
        scratchpad.add_tool_call(
            tool="audit_student_progress",
            inputs={
                "student_id": self.student.id,
                "program": self._program_label(),
                "with_plan": self.plan is not None,
            },
            output={
                "completed": audit.completed_count,
                "total": audit.total_count,
                "unmet": unmet,
            },
        )

        duration_ms = int((time.perf_counter() - started) * 1000)
        scratchpad.add_trace(
            agent=self.name,
            action="audit_student_progress",
            status="ok",
            summary=f"{audit.completed_count}/{audit.total_count} reqs satisfied"
                    + (f", {len(unmet)} unmet" if unmet else ""),
            duration_ms=duration_ms,
        )
