from app.schemas.plan import PlanRead, SemesterPlan
from app.services.planner.validator import validate_plan


def test_validator_flags_prereq_violation(fresh_student, cs_reqs, catalog):
    bad = PlanRead(
        student_id=1,
        name="Bad",
        strategy="balanced",
        terms=[SemesterPlan(term="Fall 2025", courses=["COMS W4231"])],  # no prereqs done
        summary={"program": "columbia_cs_major"},
    )
    res = validate_plan(bad, fresh_student, catalog, cs_reqs)
    codes = {w.code for w in res.warnings}
    assert "prereq_violation" in codes
    assert not res.is_valid


def test_validator_flags_credit_overload(fresh_student, cs_reqs, catalog):
    fresh_student.max_credits_per_term = 13
    fresh_student.completed_courses = ["COMS W1004", "MATH UN1101"]
    plan = PlanRead(
        student_id=1,
        name="Heavy",
        strategy="aggressive",
        terms=[
            SemesterPlan(
                term="Fall 2025",
                courses=[
                    "COMS W3134",       # 3 cr — prereq W1004 ✓
                    "COMS W3203",       # 3 cr — prereq W1004 ✓
                    "MATH UN1201",      # 3 cr — prereq UN1101 ✓
                    "ECON UN1105",      # 4 cr
                    "STAT UN1201",      # 3 cr — prereq UN1101 ✓
                ],
            )
        ],
        summary={"program": "columbia_cs_major"},
    )
    res = validate_plan(plan, fresh_student, catalog, cs_reqs)
    codes = {w.code for w in res.warnings}
    assert "credit_overload" in codes


def test_validator_flags_duplicate(fresh_student, cs_reqs, catalog):
    fresh_student.completed_courses = ["COMS W1004"]
    plan = PlanRead(
        student_id=1,
        name="Dupe",
        strategy="balanced",
        terms=[SemesterPlan(term="Fall 2025", courses=["COMS W1004"])],
        summary={"program": "columbia_cs_major"},
    )
    res = validate_plan(plan, fresh_student, catalog, cs_reqs)
    assert any(w.code == "duplicate_course" for w in res.warnings)


def test_validator_flags_term_offering(fresh_student, cs_reqs, catalog):
    fresh_student.completed_courses = [
        "COMS W1004",
        "MATH UN1101",
        "MATH UN1201",
        "COMS W3134",
        "COMS W3203",
    ]
    # COMS W4236 is Spring only
    plan = PlanRead(
        student_id=1,
        name="OffTerm",
        strategy="balanced",
        terms=[
            SemesterPlan(term="Fall 2025", courses=["COMS W3157", "MATH UN2010", "COMS W4231"]),
            SemesterPlan(term="Fall 2026", courses=["COMS W4236"]),  # Spring only
        ],
        summary={"program": "columbia_cs_major"},
    )
    res = validate_plan(plan, fresh_student, catalog, cs_reqs)
    assert any(w.code == "not_offered_in_term" for w in res.warnings)
