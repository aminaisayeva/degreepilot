"""Plan generator — deterministic.

Strategies:
  - balanced: even workload across terms, prefer breadth and prereq order
  - career_optimized: weight electives by alignment with student's career_goals
  - aggressive: pack credits to graduate earlier (cap at max_credits_per_term)

The generator produces a SemesterPlan list term-by-term. It's intentionally
greedy + heuristic — fast, predictable, and easy to explain in a demo.
"""

from __future__ import annotations

from app.models.course import Course
from app.models.requirement import Requirement, RequirementType
from app.models.student import Student
from app.schemas.plan import PlanRead, SemesterPlan
from app.services.audit.auditor import audit_student
from app.services.planner.prereq_graph import (
    assumed_completed,
    build_prereq_graph,
    prereqs_satisfied,
)
from app.services.planner.scorers import (
    career_alignment_score,
    plan_workload_variance,
    workload_score_term,
)
from app.services.planner.validator import annotate_term, validate_plan
from app.core.terms import next_term, parse_term, terms_between


def _remaining_target_courses(
    student: Student,
    requirements: list[Requirement],
    catalog: dict[str, Course],
    *,
    career_weighted: bool,
    assumed: set[str] | None = None,
) -> list[str]:
    """Compute a target set of course codes the plan must place (in priority order)."""
    completed = set(student.completed_courses or [])
    targets: list[str] = []
    seen: set[str] = set()

    # First pass: all_of, one_of — these are mandatory paths
    for r in sorted(requirements, key=lambda x: x.display_order):
        if r.type == RequirementType.ALL_OF:
            for code in r.courses:
                if code not in completed and code not in seen:
                    targets.append(code)
                    seen.add(code)
        elif r.type == RequirementType.ONE_OF:
            already = [c for c in r.courses if c in completed]
            if already:
                continue
            # Choose the most accessible / aligned option
            candidates = [c for c in r.courses if c in catalog]
            if career_weighted:
                candidates = sorted(
                    candidates,
                    key=lambda c: (
                        -career_alignment_score([catalog[c]], student.career_goals),
                        catalog[c].workload_level,
                    ),
                )
            else:
                candidates = sorted(candidates, key=lambda c: catalog[c].workload_level)
            if candidates and candidates[0] not in seen:
                targets.append(candidates[0])
                seen.add(candidates[0])
        elif r.type == RequirementType.N_OF:
            already = [c for c in r.courses if c in completed]
            need = max(r.count_required - len(already), 0)
            if need <= 0:
                continue
            candidates = [c for c in r.courses if c in catalog and c not in completed]
            if career_weighted:
                candidates = sorted(
                    candidates,
                    key=lambda c: (
                        -career_alignment_score([catalog[c]], student.career_goals),
                        catalog[c].workload_level,
                    ),
                )
            else:
                candidates = sorted(candidates, key=lambda c: catalog[c].workload_level)
            for code in candidates[:need]:
                if code not in seen:
                    targets.append(code)
                    seen.add(code)
    return _expand_with_prereqs(targets, completed | (assumed or set()), catalog)


def _expand_with_prereqs(
    targets: list[str], completed: set[str], catalog: dict[str, Course]
) -> list[str]:
    """Insert unmet prerequisite chains before their dependents.

    A target like MATH UN1201 is unschedulable until MATH UN1101 is taken, so
    every unsatisfied OR-group contributes one option (preferring courses that
    are already targets, then the lightest workload). Post-order DFS keeps
    prereqs ahead of dependents while preserving target priority.
    """
    target_lookup = set(targets)
    ordered: list[str] = []
    seen: set[str] = set()

    def visit(code: str, stack: set[str]) -> None:
        if code in seen or code in completed or code not in catalog:
            return
        if code in stack:  # cycle defense
            return
        stack.add(code)
        for group in catalog[code].prerequisites or []:
            if not group:
                continue
            if any(p in completed or p in seen for p in group):
                continue
            options = [p for p in group if p in catalog]
            if not options:
                continue
            options.sort(key=lambda c: (c not in target_lookup, catalog[c].workload_level))
            visit(options[0], stack)
        stack.discard(code)
        seen.add(code)
        ordered.append(code)

    for code in targets:
        visit(code, set())
    return ordered


def _planning_horizon(student: Student, *, allow_summer: bool = False) -> list[str]:
    seasons = ("Fall", "Spring", "Summer") if allow_summer else ("Fall", "Spring")
    return terms_between(student.current_term, student.graduation_term, seasons=seasons)


def _term_target_credits(
    student: Student,
    strategy: str,
    term_idx: int,
    total_terms: int,
    remaining_credits: float,
    remaining_terms: int,
) -> float:
    base = float(student.max_credits_per_term)
    if strategy == "aggressive":
        return base
    # Spread remaining required credits over remaining terms, then add slack
    even = remaining_credits / max(remaining_terms, 1) if remaining_credits > 0 else 13.0
    if strategy == "balanced":
        return min(base, max(13.0, even + 1.5))
    if strategy == "career_optimized":
        # slightly lighter early, heavier later
        bias = -1.0 if term_idx < total_terms / 2 else 1.0
        return min(base, max(13.0, even + bias + 1.0))
    return min(base, 14.0)


def _eligible(course: Course, completed_view: set[str], season: str) -> bool:
    if course.offered_terms and season not in course.offered_terms:
        return False
    return prereqs_satisfied(course, completed_view)


def _score_candidate(
    course: Course,
    student: Student,
    *,
    strategy: str,
    is_target: bool,
    depth: int,
    completed_view: set[str],
    unlocks: int = 0,
) -> float:
    """Higher = better candidate to place now."""
    s = 0.0
    s += 50.0 if is_target else 0.0  # mandatory > electives by default
    s += max(8 - depth, 0) * 4.0  # prefer shallow prereqs early
    s += min(unlocks, 6) * 6.0  # courses gating other pending targets go first
    if course.offered_terms and len(set(course.offered_terms)) == 1:
        s += 6.0  # single-season courses can't be deferred cheaply
    s += (5 - course.workload_level) * 1.5  # gently prefer lighter courses for balance
    # career alignment bump
    align = career_alignment_score([course], student.career_goals)
    if strategy == "career_optimized":
        s += align * 30
    else:
        s += align * 8
    # avoid scheduling capstone too early
    if "cs_capstone" in (course.categories or []):
        s -= 30  # we'll boost it manually near graduation
    return s


def _generate_one(
    student: Student,
    programs: list[str],
    requirements: list[Requirement],
    catalog: dict[str, Course],
    *,
    strategy: str,
    name: str,
) -> PlanRead:
    assumed = assumed_completed(programs, catalog)
    completed_view = set(student.completed_courses or []) | assumed
    placed: set[str] = set()
    terms_horizon = _planning_horizon(student, allow_summer=False)
    career_weighted = strategy in {"career_optimized", "aggressive"}

    target_set = _remaining_target_courses(
        student, requirements, catalog, career_weighted=career_weighted, assumed=assumed
    )
    target_set_lookup = set(target_set)

    # Available elective pool from the broader catalog, scoped to the student's
    # level: graduate programs pad with ms_track_*/grad_elective courses,
    # undergraduate programs with cs_track_*/cs_elective.
    if any(p.startswith("columbia_ms") for p in programs):
        pool_prefixes, pool_exact = ("ms_track_",), {"grad_elective"}
    else:
        pool_prefixes, pool_exact = ("cs_track_",), {"cs_elective"}
    elective_pool = [
        c.code
        for c in catalog.values()
        if c.code not in completed_view
        and c.code not in target_set_lookup
        and any(cat.startswith(pool_prefixes) or cat in pool_exact for cat in c.categories)
    ]

    graph = build_prereq_graph(list(catalog.values()))
    depths = graph.topo_levels()

    # How many pending targets each course gates (transitively, along target
    # chains) — used to pull chain heads like Intermediate Micro forward so
    # season-restricted leaves still have terms left.
    unlock_weight: dict[str, int] = {}
    for code in reversed(target_set):
        c = catalog.get(code)
        if not c:
            continue
        own = 1 + unlock_weight.get(code, 0)
        for group in c.prerequisites or []:
            for pre in group:
                unlock_weight[pre] = unlock_weight.get(pre, 0) + own

    semester_plans: list[SemesterPlan] = []
    total_terms = len(terms_horizon)

    # Estimate remaining credits across the target_set for spreading
    remaining_required_credits = sum(catalog[c].credits for c in target_set if c in catalog)

    for idx, term in enumerate(terms_horizon):
        season, _ = parse_term(term)
        unplaced_now = [c for c in target_set if c not in placed and c in catalog]
        rem_credits = sum(catalog[c].credits for c in unplaced_now)
        rem_terms = total_terms - idx
        cap = _term_target_credits(student, strategy, idx, total_terms, rem_credits, rem_terms)
        # Final term: try to schedule capstone if not already placed
        is_final_term = idx == total_terms - 1

        # Build ranked candidates
        candidates: list[tuple[float, Course, bool]] = []
        for code in list(target_set) + elective_pool:
            if code in placed or code in completed_view:
                continue
            course = catalog.get(code)
            if not course:
                continue
            if not _eligible(course, completed_view, season):
                continue
            is_target = code in target_set_lookup
            score = _score_candidate(
                course,
                student,
                strategy=strategy,
                is_target=is_target,
                depth=depths.get(code, 0),
                completed_view=completed_view,
                unlocks=unlock_weight.get(code, 0),
            )
            if is_final_term and "cs_capstone" in course.categories:
                score += 100  # ensure capstone lands at the end
            candidates.append((score, course, is_target))

        candidates.sort(key=lambda x: -x[0])

        picked: list[str] = []
        credits_used = 0.0
        workload_budget = student.preferred_workload + 3  # tolerance
        running_workload = 0.0

        for score, course, is_target in candidates:
            if credits_used + course.credits > cap:
                continue
            est_workload = course.workload_level * (course.credits / 3.0)
            # Comfort gate applies to electives only — required courses always
            # beat workload preferences, otherwise graduation slips.
            if (
                strategy == "balanced"
                and not is_target
                and running_workload + est_workload > workload_budget * 2.5
            ):
                continue
            picked.append(course.code)
            credits_used += course.credits
            running_workload += est_workload
            # stop if at minimum a "normal" load
            if strategy != "aggressive" and credits_used >= cap - 1:
                break

        # Mark planned courses as if they will be completed for downstream eligibility
        for code in picked:
            placed.add(code)
            completed_view.add(code)

        unplaced_targets = [c for c in target_set if c not in placed]

        # Skip terms where nothing was schedulable (e.g. every remaining course
        # is blocked or not offered this season) instead of emitting an empty
        # semester; a later term may still unlock the rest.
        if picked:
            sp = SemesterPlan(
                term=term,
                courses=picked,
                total_credits=round(credits_used, 2),
                workload_score=workload_score_term([catalog[c] for c in picked]),
            )
            semester_plans.append(sp)

        # Stop once all targets are placed
        if not unplaced_targets:
            break

    # Summary metrics
    audit_after = audit_student(
        Student(**{**student.model_dump(), "completed_courses": list(set(student.completed_courses or []) | placed)}),
        " + ".join(programs),
        requirements,
        catalog,
    )
    term_scores = [t.workload_score for t in semester_plans]
    summary = {
        "program": programs[0] if programs else "",
        "programs": programs,
        "strategy": strategy,
        "terms_used": len(semester_plans),
        "graduation_term": semester_plans[-1].term if semester_plans else student.graduation_term,
        "total_credits": round(sum(t.total_credits for t in semester_plans), 2),
        "career_alignment": career_alignment_score(
            [catalog[c] for t in semester_plans for c in t.courses if c in catalog],
            student.career_goals,
        ),
        "workload_variance": plan_workload_variance(term_scores),
        "post_plan_completion_pct": audit_after.overall_progress_pct,
        "unmet_requirements": [r.name for r in audit_after.requirements if not r.satisfied],
    }

    plan = PlanRead(
        student_id=student.id or 0,
        name=name,
        strategy=strategy,
        terms=semester_plans,
        summary=summary,
    )

    # Validate and attach warnings
    vr = validate_plan(plan, student, catalog, requirements)
    plan.warnings = vr.warnings
    return plan


_STRATEGY_NAMES = {
    "balanced": "Balanced Plan",
    "career_optimized": "Career-Optimized Plan",
    "aggressive": "Early-Graduation Plan",
}

# Public-facing alias (README/API docs) for the internal "aggressive" strategy.
_STRATEGY_ALIASES = {"early_graduation": "aggressive"}

KNOWN_STRATEGIES = set(_STRATEGY_NAMES) | set(_STRATEGY_ALIASES)


def generate_plans(
    student: Student,
    program: str | list[str],
    requirements: list[Requirement],
    catalog: dict[str, Course],
    *,
    strategies: list[str],
) -> list[PlanRead]:
    programs = [program] if isinstance(program, str) else list(program)
    plans: list[PlanRead] = []
    for s in strategies:
        s = _STRATEGY_ALIASES.get(s, s)
        if s not in _STRATEGY_NAMES:
            continue
        plans.append(
            _generate_one(
                student,
                programs,
                requirements,
                catalog,
                strategy=s,
                name=_STRATEGY_NAMES[s],
            )
        )
    return plans
