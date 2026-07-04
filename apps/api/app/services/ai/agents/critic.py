"""Critic agent — fully deterministic.

The Critic is the safety net that makes the multi-agent system trustworthy.
It is NOT an LLM-as-judge. It runs Python checks against the candidate
output and the deterministic engine:

  1. Plan validation — if a candidate_plan is present, run the validator
     and reject if any warning is severity=error.
  2. Course-code regex check — every course code that appears in the
     candidate_answer must appear in tool_calls or the Researcher's context.
  3. Graduation-claim check — any sentence claiming the student will
     graduate requires an audit with completed_count == total_count.
  4. Citation check — replies that quote "the bulletin says" / "according to"
     must include non-empty citations.
"""

from __future__ import annotations

import re
import time

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.plan import PlanRead, SemesterPlan
from app.services.ai.agents.scratchpad import (
    AdvisorScratchpad,
    CriticVerdict,
    CriticViolation,
)
from app.services.planner.validator import validate_plan


# Allows one- and two-letter section prefixes: "COMS W1004", "MATH UN1101", "STAT GU4001".
COURSE_CODE_RE = re.compile(r"\b[A-Z]{3,4}\s+[A-Z]{0,2}\d{3,4}[A-Z]?\b")

GRAD_CLAIM_PHRASES = (
    "graduate on time",
    "you'll be done",
    "you will be done",
    "you can finish",
    "finishes by",
    "you'll finish",
    "you will finish",
    "ready to graduate",
)

CITATION_TRIGGERS = (
    "according to",
    "the bulletin says",
    "per the bulletin",
    "policy states",
)


class Critic:
    name = "Critic"

    def __init__(
        self,
        student: Student,
        catalog: dict[str, Course],
        requirements: list[Requirement],
    ) -> None:
        self.student = student
        self.catalog = catalog
        self.requirements = requirements

    def run(self, scratchpad: AdvisorScratchpad) -> CriticVerdict:
        started = time.perf_counter()
        violations: list[CriticViolation] = []

        # 1. Plan validation (if a candidate_plan is in play)
        if scratchpad.candidate_plan is not None:
            plan = self._plan_from_dict(scratchpad.candidate_plan)
            result = validate_plan(plan, self.student, self.catalog, self.requirements)
            errors = [w for w in result.warnings if w.severity == "error"]
            for err in errors:
                violations.append(
                    CriticViolation(
                        code="plan_error",
                        message=f"{err.code}: {err.message}",
                        severity="error",
                    )
                )

        # 2. Course-code regex check on candidate_answer
        if scratchpad.candidate_answer:
            allowed = self._allowed_course_codes(scratchpad)
            mentioned = set(COURSE_CODE_RE.findall(scratchpad.candidate_answer))
            ungrounded = mentioned - allowed
            for code in sorted(ungrounded):
                violations.append(
                    CriticViolation(
                        code="hallucinated_code",
                        message=f"Reply mentions {code!r} but no tool call or context produced it.",
                        severity="error",
                    )
                )

        # 3. Graduation-claim check
        if scratchpad.candidate_answer:
            lowered = scratchpad.candidate_answer.lower()
            if any(phrase in lowered for phrase in GRAD_CLAIM_PHRASES):
                audit = scratchpad.context.get("audit") or {}
                completed = audit.get("completed_count", 0)
                total = audit.get("total_count", 0)
                if not (total > 0 and completed == total):
                    violations.append(
                        CriticViolation(
                            code="ungrounded_grad_claim",
                            message=(
                                "Reply claims the student can graduate, but the most recent "
                                f"audit shows {completed}/{total} requirements satisfied."
                            ),
                            severity="error",
                        )
                    )

        # 4. Citation check
        if scratchpad.candidate_answer:
            lowered = scratchpad.candidate_answer.lower()
            if any(trigger in lowered for trigger in CITATION_TRIGGERS):
                # The advisor schema collects citations from tool outputs.
                has_citations = any(
                    tc.tool == "answer_policy_question_from_sources"
                    for tc in scratchpad.tool_calls
                )
                if not has_citations:
                    violations.append(
                        CriticViolation(
                            code="missing_citation",
                            message=(
                                "Reply makes a sourced claim ('according to' / 'the bulletin says') "
                                "but no citation tool was called."
                            ),
                            severity="warning",
                        )
                    )

        verdict = CriticVerdict(
            ok=not any(v.severity == "error" for v in violations),
            violations=violations,
        )
        scratchpad.critic_verdict = verdict

        duration_ms = int((time.perf_counter() - started) * 1000)
        if verdict.ok:
            summary = f"approved ({len(violations)} non-blocking)" if violations else "approved"
            status = "ok"
        else:
            blockers = [v.code for v in violations if v.severity == "error"]
            summary = f"rejected: {', '.join(blockers)}"
            status = "rejected"
        scratchpad.add_trace(
            agent=self.name,
            action="verify",
            status=status,
            summary=summary,
            duration_ms=duration_ms,
        )
        return verdict

    # ----- helpers -----

    def _allowed_course_codes(self, scratchpad: AdvisorScratchpad) -> set[str]:
        """Codes the Critic considers grounded — i.e., that an upstream agent
        actually produced via tool calls or via the catalog known to the Researcher."""
        allowed: set[str] = set(scratchpad.context.get("known_course_codes") or [])
        allowed.update(scratchpad.context.get("completed_courses") or [])
        for t in scratchpad.context.get("plan_terms") or []:
            allowed.update(t.get("courses") or [])
        for tc in scratchpad.tool_calls:
            allowed.update(self._codes_in(tc.output))
        return allowed

    def _codes_in(self, obj) -> set[str]:
        """Walk an arbitrary JSON-ish structure and pull course-code-shaped strings."""
        codes: set[str] = set()
        if isinstance(obj, str):
            codes.update(COURSE_CODE_RE.findall(obj))
        elif isinstance(obj, dict):
            for v in obj.values():
                codes.update(self._codes_in(v))
        elif isinstance(obj, (list, tuple, set)):
            for v in obj:
                codes.update(self._codes_in(v))
        return codes

    def _plan_from_dict(self, data: dict) -> PlanRead:
        terms = [
            SemesterPlan(
                term=t.get("term", ""),
                courses=list(t.get("courses", [])),
                total_credits=float(t.get("total_credits", 0)),
                workload_score=float(t.get("workload_score", 0)),
            )
            for t in (data.get("terms") or [])
        ]
        return PlanRead(
            id=data.get("id"),
            student_id=data.get("student_id", 0),
            name=data.get("name", "candidate"),
            strategy=data.get("strategy", "candidate"),
            terms=terms,
            warnings=data.get("warnings", []),
            summary=data.get("summary", {}),
        )
