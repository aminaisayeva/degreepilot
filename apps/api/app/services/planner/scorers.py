"""Workload + career alignment scorers."""

from __future__ import annotations

from app.models.course import Course


def workload_score_term(courses: list[Course]) -> float:
    """Sum of workload levels weighted by credits, normalized to 0-10ish.

    Light = ~2, normal full load (4 courses x level 3) = ~6-7, brutal = 10+.
    """
    if not courses:
        return 0.0
    raw = sum(c.workload_level * (c.credits / 3.0) for c in courses)
    return round(raw, 2)


def career_alignment_score(courses: list[Course], goals: list[str]) -> float:
    """Fraction of courses (weighted by credits) whose career_tags intersect goals.

    Returns a score in [0, 1].
    """
    if not goals:
        return 0.0
    goal_set = {g.lower() for g in goals}
    total = 0.0
    matched = 0.0
    for c in courses:
        w = max(c.credits, 0.0)
        total += w
        tags = {t.lower() for t in (c.career_tags or [])}
        if tags & goal_set:
            matched += w
    return round(matched / total, 3) if total else 0.0


def plan_workload_variance(term_scores: list[float]) -> float:
    """Sample variance of term workload scores; lower = more balanced."""
    if len(term_scores) < 2:
        return 0.0
    mean = sum(term_scores) / len(term_scores)
    return round(sum((s - mean) ** 2 for s in term_scores) / len(term_scores), 3)
