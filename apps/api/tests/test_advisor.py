from app.schemas.advisor import AdvisorRequest
from app.services.ai.advisor import answer_advisor, classify_intent
from app.services.planner.generator import generate_plans


def test_classify_intent_graduation():
    assert classify_intent("Can I graduate on time?") == "graduation_feasibility"


def test_classify_intent_missing():
    assert classify_intent("What requirements am I still missing?") == "missing_requirements"


def test_classify_intent_study_abroad():
    assert classify_intent("What if I study abroad junior spring?") == "study_abroad"


def test_classify_intent_ai_ml():
    assert classify_intent("Which courses are best for AI/ML?") == "ai_ml_picks"


def test_classify_intent_recommendation():
    assert classify_intent("Why did you recommend this course?") == "recommendation_rationale"


def test_classify_intent_risk():
    assert classify_intent("What's the risk in this plan?") == "plan_risk"


def test_advisor_runs_audit_for_grad_question(midway_student, cs_reqs, catalog):
    req = AdvisorRequest(student_id=midway_student.id, message="Can I graduate on time?")
    res = answer_advisor(req, midway_student, catalog, cs_reqs)
    assert res.intent == "graduation_feasibility"
    assert any(tc.tool == "audit_student" for tc in res.tool_calls)
    assert res.answer


def test_advisor_uses_plan_when_provided(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student,
        "columbia_cs_major",
        cs_reqs,
        catalog,
        strategies=["balanced"],
    )
    req = AdvisorRequest(
        student_id=midway_student.id, message="What's the risk in this plan?", plan_id=None
    )
    res = answer_advisor(req, midway_student, catalog, cs_reqs, plans[0])
    assert res.intent == "plan_risk"
    assert any(tc.tool == "validate_plan" for tc in res.tool_calls)


def test_advisor_ml_picks(midway_student, cs_reqs, catalog):
    req = AdvisorRequest(student_id=midway_student.id, message="What's good for ML?")
    res = answer_advisor(req, midway_student, catalog, cs_reqs)
    assert res.intent == "ai_ml_picks"
    assert res.tool_calls[0].tool == "career_track_picks"
    assert res.tool_calls[0].output["picks"]


def test_advisor_grad_answer_reflects_unmet_requirements(fresh_student, cs_reqs, catalog):
    # A student with everything left must NOT be told every requirement clears.
    req = AdvisorRequest(student_id=1, message="Can I graduate on time?")
    res = answer_advisor(req, fresh_student, catalog, cs_reqs)
    assert res.intent == "graduation_feasibility"
    assert "every requirement clears" not in res.answer
    assert "requirement(s) open" in res.answer
