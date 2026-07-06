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


def test_waived_courses_do_not_leak_into_simulated_credit_audit(session, catalog, ms_reqs, ms_student):
    from app.models.requirement import Requirement, RequirementType
    from app.schemas.plan import PlanRead, SemesterPlan
    from app.services.planner.validator import validate_plan

    reqs = list(ms_reqs) + [Requirement(
        id=999, program="columbia_ms_cs", name="Total: 30 points",
        type=RequirementType.CREDITS, courses=[], credits_required=30, display_order=90)]
    ms_student.waived_courses = ["COMS W4118", "COMS W4231", "COMS W4701"]
    plan = PlanRead(student_id=3, name="P", strategy="balanced", terms=[
        SemesterPlan(term="Fall 2025", courses=["COMS E6998", "COMS E6261"],
                     total_credits=6, workload_score=6),
    ], warnings=[], summary={"program": "columbia_ms_cs"})
    result = validate_plan(plan, ms_student, catalog, reqs)
    codes = [w.code for w in result.warnings]
    # 6 real credits + waived-not-counted => the 30-point card must be unmet
    assert "unmet_graduation" in codes
    # and the shortfall is called out with actionable advice
    assert "credit_shortfall" in codes
    shortfall = next(w for w in result.warnings if w.code == "credit_shortfall")
    assert "credits/term" in shortfall.message


def test_part_time_enrollment_thresholds(session, catalog, ms_reqs, ms_student):
    """Part-time students (constraints.enrollment) get a 6-credit floor and
    their real cap is respected instead of being lifted to 12."""
    from app.schemas.plan import PlanRead, SemesterPlan
    from app.services.planner.validator import validate_plan

    ms_student.constraints = {**(ms_student.constraints or {}), "enrollment": "part_time"}
    ms_student.max_credits_per_term = 8
    plan = PlanRead(student_id=3, name="P", strategy="balanced", terms=[
        SemesterPlan(term="Fall 2025", courses=["COMS W4118", "COMS W4111", "COMS W4115"],
                     total_credits=9, workload_score=9),   # 9 > cap 8 → overload
        SemesterPlan(term="Spring 2026", courses=["COMS W4231", "COMS W4701"],
                     total_credits=6, workload_score=6),   # 6 ≥ PT floor → no part_time_load
    ], warnings=[], summary={"program": "columbia_ms_cs"})
    result = validate_plan(plan, ms_student, catalog, ms_reqs)
    codes = [w.code for w in result.warnings]
    assert "credit_overload" in codes          # real cap of 8 enforced
    assert "part_time_load" not in codes       # 6 credits is fine part-time
