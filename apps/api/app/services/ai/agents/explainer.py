"""Explainer agent — phrases the final reply.

In v1 it reuses the existing DeterministicProvider templates. In v1.1 the
Explainer is the second natural place to wire a real LLM (the first being
the Planner).

The Explainer also handles the "Critic rejected after max retries" path —
it produces an honest "I couldn't find a safe answer" message instead of
faking success.
"""

from __future__ import annotations

import time

from app.services.ai.agents.scratchpad import AdvisorScratchpad, CriticVerdict
from app.services.ai.provider import DeterministicProvider, LLMProvider


SUGGESTIONS_BY_INTENT: dict[str, list[str]] = {
    "graduation_feasibility": [
        "Show me what's missing",
        "What if I study abroad junior spring?",
        "What are the risks in this plan?",
    ],
    "missing_requirements": [
        "Why did you recommend this plan?",
        "Best courses for AI/ML?",
        "Can I graduate on time?",
    ],
    "study_abroad": [
        "What if I shift those courses earlier?",
        "What's the risk in this plan?",
    ],
    "ai_ml_picks": [
        "Why did you recommend these?",
        "Which one should I take first?",
    ],
    "plan_risk": [
        "Can I graduate on time?",
        "What if I study abroad junior spring?",
    ],
}


class Explainer:
    name = "Explainer"

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or DeterministicProvider()

    def run(self, scratchpad: AdvisorScratchpad) -> None:
        started = time.perf_counter()

        if scratchpad.candidate_answer:
            # Planner already drafted something the Critic approved — keep it.
            answer = scratchpad.candidate_answer
        else:
            answer = self._compose(scratchpad)

        # If the Critic ultimately couldn't approve anything, honestly say so.
        verdict = scratchpad.critic_verdict
        if verdict and not verdict.ok:
            answer = self._honest_failure_message(verdict)

        intent = scratchpad.intent or "general"
        suggestions = SUGGESTIONS_BY_INTENT.get(intent, [])

        scratchpad.final_response = {
            "intent": intent,
            "answer": answer,
            "suggestions": suggestions,
            "citations": [f"DegreePilot/{tc.tool}" for tc in scratchpad.tool_calls],
        }

        scratchpad.add_trace(
            agent=self.name,
            action="compose",
            status="ok",
            summary=f"reply ({len(answer)} chars)",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    # ----- composing -----

    def _compose(self, scratchpad: AdvisorScratchpad) -> str:
        intent = scratchpad.intent or "general"
        context = self._build_provider_context(scratchpad)
        return self.provider.explain(intent, context)

    def _build_provider_context(self, scratchpad: AdvisorScratchpad) -> dict:
        ctx = dict(scratchpad.context)
        # Provider templates look up specific keys — keep the shape stable.
        audit = ctx.get("audit") or {}
        ctx.setdefault("unmet", audit.get("unmet", []))
        return ctx

    def _honest_failure_message(self, verdict: CriticVerdict) -> str:
        blockers = [v.message for v in verdict.violations if v.severity == "error"]
        if not blockers:
            return "I couldn't compose a safe answer this turn. Try rephrasing."
        head = "I couldn't find a safe answer because:"
        bullets = "\n".join(f"  - {m}" for m in blockers[:4])
        tail = "Try narrowing the question or generating a plan first if you haven't."
        return f"{head}\n{bullets}\n{tail}"
