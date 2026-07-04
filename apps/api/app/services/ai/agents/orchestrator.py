"""Orchestrator agent — routes the message and runs the loop.

Workflow:
  1. Classify intent.
  2. Run Researcher.
  3. If the intent benefits from planning, run Planner.
  4. Run Critic.
  5. If Critic rejects, loop back to Planner up to MAX_RETRIES times.
  6. Run Explainer.

The Orchestrator owns the retry budget and the routing matrix.
"""

from __future__ import annotations

import re

from app.models.course import Course
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.plan import PlanRead
from app.services.ai.agents.critic import Critic
from app.services.ai.agents.explainer import Explainer
from app.services.ai.agents.planner import Planner
from app.services.ai.agents.researcher import Researcher
from app.services.ai.agents.scratchpad import AdvisorScratchpad
from app.services.ai.provider import LLMProvider


MAX_RETRIES = 3


# Intents that need the Planner to propose something.
PLANNING_INTENTS = {"study_abroad", "ai_ml_picks", "plan_risk", "recommendation_rationale"}


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


class Orchestrator:
    name = "Orchestrator"

    def __init__(
        self,
        student: Student,
        catalog: dict[str, Course],
        requirements: list[Requirement],
        plan: PlanRead | None = None,
        provider: LLMProvider | None = None,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.student = student
        self.catalog = catalog
        self.requirements = requirements
        self.plan = plan
        self.provider = provider
        self.max_retries = max_retries

        self.researcher = Researcher(student, catalog, requirements, plan)
        self.planner = Planner(student, catalog, requirements, plan)
        self.critic = Critic(student, catalog, requirements)
        self.explainer = Explainer(provider=provider)

    def run(
        self,
        user_message: str,
        student_id: int,
        plan_id: int | None = None,
    ) -> AdvisorScratchpad:
        scratchpad = AdvisorScratchpad(
            user_message=user_message,
            student_id=student_id,
            plan_id=plan_id,
        )

        # 1. Intent
        scratchpad.intent = classify_intent(user_message)
        scratchpad.add_trace(
            agent=self.name,
            action="classify_intent",
            status="ok",
            summary=f"intent={scratchpad.intent}",
        )

        # 2. Researcher
        self.researcher.run(scratchpad)

        # 3. Planner (only for planning intents) + Critic (always) with retries
        if scratchpad.intent in PLANNING_INTENTS:
            self.planner.run(scratchpad)

        # Compose a draft answer before the Critic checks it. The Critic needs
        # something to verify; for info intents, the Explainer drafts first.
        draft = self._draft_answer(scratchpad)
        scratchpad.candidate_answer = draft

        verdict = self.critic.run(scratchpad)
        retries = 0
        while not verdict.ok and retries < self.max_retries:
            retries += 1
            scratchpad.retry_count = retries
            scratchpad.add_trace(
                agent=self.name,
                action="retry",
                status="retry",
                summary=f"retry {retries}/{self.max_retries}",
            )
            # Re-run the planning step (which has access to scratchpad.critic_verdict).
            if scratchpad.intent in PLANNING_INTENTS:
                self.planner.run(scratchpad)
            scratchpad.candidate_answer = self._draft_answer(scratchpad)
            verdict = self.critic.run(scratchpad)

        # 4. Explainer (will use candidate_answer if approved, else honest failure)
        self.explainer.run(scratchpad)
        return scratchpad

    # ----- helpers -----

    def _draft_answer(self, scratchpad: AdvisorScratchpad) -> str:
        """Use the Explainer's provider to produce a draft we can verify."""
        intent = scratchpad.intent or "general"
        ctx = dict(scratchpad.context)
        audit = ctx.get("audit") or {}
        ctx.setdefault("unmet", audit.get("unmet", []))
        return self.explainer.provider.explain(intent, ctx)
