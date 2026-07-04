"""LLM provider abstraction.

The MVP intentionally ships with a `DeterministicProvider` that produces
explanations from templates + tool outputs. A real LLM (hosted API or local
model) can be plugged in by implementing `LLMProvider`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def explain(self, intent: str, context: dict) -> str:
        ...


class DeterministicProvider(LLMProvider):
    name = "deterministic"

    def explain(self, intent: str, context: dict) -> str:
        # Templates per intent. Each receives `context` populated by the
        # advisor with deterministic tool outputs (audit, plan, comparison).
        if intent == "graduation_feasibility":
            unmet = context.get("unmet", [])
            if not unmet:
                return (
                    f"Yes — with your current plan you finish by {context.get('graduation_term')}, "
                    "and every requirement clears. Hold steady."
                )
            return (
                f"Almost — by {context.get('graduation_term')} you'd still have "
                f"{len(unmet)} requirement(s) open: {', '.join(unmet[:4])}"
                + ("…" if len(unmet) > 4 else ".")
            )
        if intent == "missing_requirements":
            unmet = context.get("unmet", [])
            if not unmet:
                return "You're not missing anything tracked — your audit is fully green."
            return (
                f"You still need: {', '.join(unmet[:6])}"
                + ("…" if len(unmet) > 6 else ".")
                + " Knocking these out earliest reduces graduation risk."
            )
        if intent == "study_abroad":
            term = context.get("term", "your chosen term")
            blockers = context.get("blockers", [])
            if not blockers:
                return (
                    f"Going abroad in {term} looks doable — nothing required for graduation is "
                    f"only offered then in your current plan."
                )
            return (
                f"If you study abroad in {term}, you'd skip {len(blockers)} course(s) "
                f"that are core: {', '.join(blockers[:4])}. You can either pre-take them, "
                "shift them later, or pick equivalent transfer credit."
            )
        if intent == "ai_ml_picks":
            picks = context.get("picks", [])
            return (
                "For AI/ML, prioritize: " + ", ".join(picks)
                + ". They satisfy the AI track depth while compounding into each other."
            )
        if intent == "recommendation_rationale":
            return (
                "I picked these courses because they (a) sit on the prereq path for later "
                "requirements, (b) match your career goals, and (c) keep workload balanced. "
                "Each is offered in the term I placed it in."
            )
        if intent == "plan_risk":
            risks = context.get("risks", [])
            if not risks:
                return "No structural risks detected — workload is balanced and prereqs check out."
            return "Risks I'm watching: " + "; ".join(risks[:5]) + "."
        return (
            "I'd need a planned schedule to answer that precisely. Generate a plan first "
            "and I'll reason about it concretely."
        )
