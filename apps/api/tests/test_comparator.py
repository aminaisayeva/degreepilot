from app.services.planner.comparator import compare_plans
from app.services.planner.generator import generate_plans


def test_compare_picks_winner_with_rationale(midway_student, cs_reqs, catalog):
    plans = generate_plans(
        midway_student,
        "columbia_cs_major",
        cs_reqs,
        catalog,
        strategies=["balanced", "career_optimized"],
    )
    result = compare_plans(midway_student, plans, cs_reqs, catalog)
    assert result.winner in {p.name for p in plans}
    assert len(result.summaries) == 2
    assert len(result.audits) == 2
    assert result.rationale
