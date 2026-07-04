from app.services.planner.scorers import (
    career_alignment_score,
    plan_workload_variance,
    workload_score_term,
)


def test_workload_zero_for_empty():
    assert workload_score_term([]) == 0.0


def test_workload_grows_with_difficulty(catalog):
    light = workload_score_term([catalog["COMS W1004"]])
    heavy = workload_score_term([catalog["COMS W4118"]])
    assert heavy > light


def test_career_alignment_zero_without_goals(catalog):
    assert career_alignment_score([catalog["COMS W4771"]], []) == 0.0


def test_career_alignment_picks_aligned(catalog):
    aligned = career_alignment_score([catalog["COMS W4771"]], ["ai_ml"])
    unaligned = career_alignment_score([catalog["MATH UN1101"]], ["ai_ml"])
    assert aligned > unaligned


def test_workload_variance_zero_for_flat():
    assert plan_workload_variance([5.0, 5.0, 5.0]) == 0.0


def test_workload_variance_positive_for_uneven():
    assert plan_workload_variance([2.0, 10.0]) > 0
