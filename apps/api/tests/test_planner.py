from app.services.planner.generator import generate_plans


def test_generate_two_variants(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student,
        "columbia_cs_major",
        cs_reqs,
        catalog,
        strategies=["balanced", "career_optimized"],
    )
    assert len(plans) == 2
    assert {p.name for p in plans} == {"Balanced Plan", "Career-Optimized Plan"}


def test_plans_respect_credit_cap(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student, "columbia_cs_major", cs_reqs, catalog, strategies=["balanced"]
    )
    for t in plans[0].terms:
        assert t.total_credits <= midway_student.max_credits_per_term


def test_plans_have_no_prereq_errors(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student,
        "columbia_cs_major",
        cs_reqs,
        catalog,
        strategies=["balanced", "career_optimized", "aggressive"],
    )
    for p in plans:
        prereq_errs = [w for w in p.warnings if w.code == "prereq_violation"]
        assert prereq_errs == [], f"{p.name} had prereq violations: {prereq_errs}"


def test_plans_close_all_requirements(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student, "columbia_cs_major", cs_reqs, catalog, strategies=["balanced"]
    )
    p = plans[0]
    assert p.summary["unmet_requirements"] == []
    assert p.summary["post_plan_completion_pct"] >= 0.99


def test_fresh_student_plan_closes_all_requirements(fresh_student, cs_reqs, catalog):
    # A brand-new student has no prereqs done — the generator must schedule
    # prereq chains (e.g. MATH UN1101 before MATH UN1201) to close every requirement.
    plans = generate_plans(
        fresh_student, "columbia_cs_major", cs_reqs, catalog, strategies=["balanced"]
    )
    p = plans[0]
    assert p.summary["unmet_requirements"] == []
    prereq_errs = [w for w in p.warnings if w.code == "prereq_violation"]
    assert prereq_errs == []


def test_early_graduation_strategy_alias(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student, "columbia_cs_major", cs_reqs, catalog, strategies=["early_graduation"]
    )
    assert len(plans) == 1
    assert plans[0].name == "Early-Graduation Plan"


def test_career_optimized_has_higher_or_equal_alignment(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student,
        "columbia_cs_major",
        cs_reqs,
        catalog,
        strategies=["balanced", "career_optimized"],
    )
    balanced = next(p for p in plans if p.strategy == "balanced")
    career = next(p for p in plans if p.strategy == "career_optimized")
    assert career.summary["career_alignment"] >= balanced.summary["career_alignment"]


def test_ms_student_plan_closes_all_requirements(ms_student, ms_reqs, catalog):
    # A fresh MS student (CS bachelor's assumed) must get a fully-closing plan
    # with only graduate-eligible courses — no undergrad prereqs scheduled.
    plans = generate_plans(
        ms_student, ["columbia_ms_cs"], ms_reqs, catalog, strategies=["balanced"]
    )
    p = plans[0]
    assert p.summary["unmet_requirements"] == []
    assert [w for w in p.warnings if w.severity == "error"] == []
    for t in p.terms:
        for code in t.courses:
            level = int("".join(ch for ch in code if ch.isdigit()))
            assert level >= 4000, f"undergrad course {code} scheduled in MS plan"


def test_ms_plan_total_credits_meet_30_points(ms_student, ms_reqs, catalog):
    plans = generate_plans(
        ms_student, ["columbia_ms_cs"], ms_reqs, catalog, strategies=["balanced"]
    )
    assert plans[0].summary["total_credits"] >= 30


def test_waived_courses_are_never_scheduled(session, catalog, ms_reqs, ms_student):
    from app.services.planner.generator import generate_plans

    ms_student.waived_courses = ["COMS W4118", "COMS W4231"]
    plans = generate_plans(ms_student, ["columbia_ms_cs"], ms_reqs, catalog,
                           strategies=["balanced"])
    scheduled = {c for t in plans[0].terms for c in t.courses}
    assert "COMS W4118" not in scheduled
    assert "COMS W4231" not in scheduled
    # The horizon still gets filled with other courses (waivers earn no credit).
    assert sum(t.total_credits for t in plans[0].terms) >= 24


def test_research_option_schedules_e6901(session, catalog, ms_reqs, ms_student):
    from app.services.planner.generator import generate_plans

    ms_student.constraints = {**(ms_student.constraints or {}), "include_research": True}
    plans = generate_plans(ms_student, ["columbia_ms_cs"], ms_reqs, catalog,
                           strategies=["balanced"])
    scheduled = {c for t in plans[0].terms for c in t.courses}
    assert "COMS E6901" in scheduled


def test_no_research_by_default(session, catalog, ms_reqs, ms_student):
    from app.services.planner.generator import generate_plans

    plans = generate_plans(ms_student, ["columbia_ms_cs"], ms_reqs, catalog,
                           strategies=["balanced"])
    scheduled = {c for t in plans[0].terms for c in t.courses}
    assert "COMS E6901" not in scheduled


def test_generator_fills_to_credits_floor_despite_waivers(session, catalog, ms_reqs, ms_student):
    """Waiving most course cards must not shrink the plan: CREDITS-type
    requirements (Total: 30 points) still need real courses scheduled."""
    from app.models.requirement import Requirement, RequirementType
    from app.services.planner.generator import generate_plans

    reqs = list(ms_reqs) + [Requirement(
        id=999, program="columbia_ms_cs", name="Total: 30 points",
        type=RequirementType.CREDITS, courses=[], credits_required=30,
        display_order=90,
    )]
    # Production catalogs carry loader-derived categories (ms_grad_eligible);
    # mirror that so the padding pool matches reality.
    from app.seed.loader import _number_int, derive_categories
    for c in catalog.values():
        for cat in derive_categories(c.code, c.department,
                                     _number_int(c.code.split()[-1]), c.credits):
            if cat not in c.categories:
                c.categories = [*c.categories, cat]
    # Waive enough to satisfy nearly every course card.
    ms_student.waived_courses = [
        "COMS W4118", "COMS W4231", "COMS W4701",
        "COMS E6111", "COMS E6118", "COMS E6156", "COMS E6232",
        "COMS W4156", "COMS W4170", "COMS W4181",
    ]
    plans = generate_plans(ms_student, ["columbia_ms_cs"], reqs, catalog,
                           strategies=["balanced"])
    total = sum(t.total_credits for t in plans[0].terms)
    assert total >= 30, f"only {total} credits planned across {len(plans[0].terms)} terms"
    assert len(plans[0].terms) >= 3
