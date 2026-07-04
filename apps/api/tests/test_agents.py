"""Tests for the multi-agent advisor.

Coverage:
  - Researcher populates context + tool_calls.
  - Critic blocks hallucinated course codes.
  - Critic blocks ungrounded graduation claims.
  - Critic blocks plans with prereq violations.
  - Critic approves clean replies.
  - Orchestrator end-to-end for each intent.
  - Orchestrator triggers retry when Critic rejects.
"""

from __future__ import annotations

import pytest

from app.schemas.plan import PlanRead, SemesterPlan
from app.services.ai.agents.critic import Critic
from app.services.ai.agents.explainer import Explainer
from app.services.ai.agents.orchestrator import Orchestrator, classify_intent
from app.services.ai.agents.planner import Planner
from app.services.ai.agents.researcher import Researcher
from app.services.ai.agents.scratchpad import AdvisorScratchpad
from app.services.planner.generator import generate_plans


# ----------------------------- intent classification -----------------------------

@pytest.mark.parametrize("message,expected", [
    ("Can I graduate on time?", "graduation_feasibility"),
    ("What requirements am I missing?", "missing_requirements"),
    ("What if I study abroad junior spring?", "study_abroad"),
    ("Best courses for AI/ML?", "ai_ml_picks"),
    ("Why did you recommend this plan?", "recommendation_rationale"),
    ("What's the risk in this plan?", "plan_risk"),
    ("Hello!", "general"),
])
def test_classify_intent(message, expected):
    assert classify_intent(message) == expected


# ----------------------------- Researcher -----------------------------

def test_researcher_populates_context(midway_student, cs_reqs, catalog):
    r = Researcher(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="anything", student_id=midway_student.id)
    r.run(sp)
    assert "audit" in sp.context
    assert sp.context["audit"]["total_count"] > 0
    assert sp.context["known_course_codes"]
    # one audit tool call recorded
    assert any(tc.tool == "audit_student_progress" for tc in sp.tool_calls)
    # one trace entry
    assert sp.agent_trace[-1].agent == "Researcher"


# ----------------------------- Critic -----------------------------

def test_critic_blocks_hallucinated_course(midway_student, cs_reqs, catalog):
    c = Critic(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="x", student_id=midway_student.id)
    sp.context["known_course_codes"] = list(catalog.keys())
    sp.candidate_answer = "You should definitely take COMS W9999 next semester."
    verdict = c.run(sp)
    assert not verdict.ok
    assert any(v.code == "hallucinated_code" for v in verdict.violations)


def test_critic_allows_grounded_course(midway_student, cs_reqs, catalog):
    c = Critic(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="x", student_id=midway_student.id)
    sp.context["known_course_codes"] = list(catalog.keys())
    sp.candidate_answer = "You've already taken COMS W1004 — nice."
    verdict = c.run(sp)
    assert verdict.ok


def test_critic_blocks_ungrounded_grad_claim(midway_student, cs_reqs, catalog):
    c = Critic(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="x", student_id=midway_student.id)
    sp.context["known_course_codes"] = list(catalog.keys())
    sp.context["audit"] = {"completed_count": 4, "total_count": 11, "unmet": ["X"]}
    sp.candidate_answer = "Yes, you can graduate on time without any issues."
    verdict = c.run(sp)
    assert not verdict.ok
    assert any(v.code == "ungrounded_grad_claim" for v in verdict.violations)


def test_critic_allows_grounded_grad_claim(midway_student, cs_reqs, catalog):
    c = Critic(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="x", student_id=midway_student.id)
    sp.context["known_course_codes"] = list(catalog.keys())
    sp.context["audit"] = {"completed_count": 11, "total_count": 11, "unmet": []}
    sp.candidate_answer = "Yes — you can graduate on time."
    verdict = c.run(sp)
    assert verdict.ok


def test_critic_blocks_plan_with_prereq_violation(midway_student, cs_reqs, catalog):
    c = Critic(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="x", student_id=midway_student.id)
    sp.context["known_course_codes"] = list(catalog.keys())
    # Plan that schedules COMS W4231 with no prereqs done.
    sp.candidate_plan = {
        "student_id": midway_student.id,
        "name": "candidate",
        "strategy": "candidate",
        "terms": [{"term": "Fall 2025", "courses": ["COMS W4771"], "total_credits": 3, "workload_score": 5}],
        "warnings": [],
        "summary": {"program": "columbia_cs_major"},
    }
    sp.candidate_answer = "Take COMS W4771 first term."
    verdict = c.run(sp)
    assert not verdict.ok
    assert any(v.code == "plan_error" for v in verdict.violations)


# ----------------------------- Planner -----------------------------

def test_planner_ai_ml_picks(midway_student, cs_reqs, catalog):
    p = Planner(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="best ml", student_id=midway_student.id)
    sp.intent = "ai_ml_picks"
    p.run(sp)
    assert sp.context.get("picks")
    assert any(tc.tool == "career_track_picks" for tc in sp.tool_calls)


def test_planner_no_op_for_info_intent(midway_student, cs_reqs, catalog):
    p = Planner(midway_student, catalog, cs_reqs)
    sp = AdvisorScratchpad(user_message="grad?", student_id=midway_student.id)
    sp.intent = "graduation_feasibility"
    pre_calls = len(sp.tool_calls)
    p.run(sp)
    assert len(sp.tool_calls) == pre_calls  # no extra tool calls
    assert sp.agent_trace[-1].action == "no_op"


# ----------------------------- Orchestrator (end-to-end) -----------------------------

def test_orchestrator_graduation_question(midway_student, cs_reqs, catalog):
    orch = Orchestrator(midway_student, catalog, cs_reqs)
    sp = orch.run("Can I graduate on time?", student_id=midway_student.id)
    assert sp.intent == "graduation_feasibility"
    assert sp.final_response is not None
    assert sp.final_response["answer"]
    # Trace contains all key agents
    agents = [t.agent for t in sp.agent_trace]
    assert "Researcher" in agents
    assert "Critic" in agents
    assert "Explainer" in agents


def test_orchestrator_ai_ml_question(midway_student, cs_reqs, catalog):
    orch = Orchestrator(midway_student, catalog, cs_reqs)
    sp = orch.run("Best courses for AI/ML?", student_id=midway_student.id)
    assert sp.intent == "ai_ml_picks"
    assert sp.final_response is not None
    # Planner ran
    assert any(t.agent == "Planner" and t.status == "ok" for t in sp.agent_trace)
    # Critic approved
    assert sp.critic_verdict is not None and sp.critic_verdict.ok


def test_orchestrator_plan_risk_with_plan(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student, "columbia_cs_major", cs_reqs, catalog, strategies=["balanced"]
    )
    orch = Orchestrator(midway_student, catalog, cs_reqs, plan=plans[0])
    sp = orch.run("What's the risk in this plan?", student_id=midway_student.id)
    assert sp.intent == "plan_risk"
    assert any(tc.tool == "validate_plan" for tc in sp.tool_calls)


def test_orchestrator_records_retry_on_critic_rejection(midway_student, cs_reqs, catalog):
    """Force the Critic to reject by patching the Explainer's provider to
    produce a reply containing a hallucinated course code."""

    class BadProvider:
        name = "bad"

        def explain(self, intent, context):
            return "I think you should take COMS W9999 next semester."

    orch = Orchestrator(midway_student, catalog, cs_reqs, provider=BadProvider())
    sp = orch.run("anything", student_id=midway_student.id)
    # All retries should fail; final response is the honest failure message.
    assert sp.retry_count == orch.max_retries
    assert sp.final_response is not None
    assert "couldn't" in sp.final_response["answer"].lower()
    # Trace should show the retry attempts
    retries = [t for t in sp.agent_trace if t.status == "retry"]
    assert len(retries) >= 1


def test_orchestrator_final_response_contains_suggestions(midway_student, cs_reqs, catalog):
    orch = Orchestrator(midway_student, catalog, cs_reqs)
    sp = orch.run("Can I graduate on time?", student_id=midway_student.id)
    assert sp.final_response is not None
    assert "suggestions" in sp.final_response
    assert isinstance(sp.final_response["suggestions"], list)
