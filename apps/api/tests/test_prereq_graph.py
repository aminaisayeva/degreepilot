from app.services.planner.prereq_graph import (
    build_prereq_graph,
    missing_prereqs,
    prereqs_satisfied,
)


def test_prereq_satisfied_handles_or_groups(catalog):
    # COMS W3134 prereq: (COMS W1004 OR COMS W1007)
    ds = catalog["COMS W3134"]
    assert prereqs_satisfied(ds, {"COMS W1004"})
    assert prereqs_satisfied(ds, {"COMS W1007"})
    assert not prereqs_satisfied(ds, set())


def test_prereq_unsatisfied_returns_missing_groups(catalog):
    # COMS W4771 prereqs include linear-algebra OR-group + prob/stat OR-group
    ml = catalog["COMS W4771"]
    missing = missing_prereqs(ml, {"COMS W3134"})
    assert missing  # at least one group still missing
    assert any("MATH UN2010" in g for g in missing)


def test_topo_levels_have_intro_at_zero(catalog):
    g = build_prereq_graph(list(catalog.values()))
    depths = g.topo_levels()
    assert depths["COMS W1004"] == 0
    assert depths["COMS W3134"] >= 1
    assert depths["COMS W4771"] >= depths["COMS W3134"]


def test_unlocks_are_reachable(catalog):
    g = build_prereq_graph(list(catalog.values()))
    unlocks = g.unlocks("COMS W3134")
    assert "COMS W4231" in unlocks or "COMS W3157" in unlocks


def test_math_majors_are_not_graduate_programs(catalog):
    """Prefix guard: 'columbia_math_*' must NOT match the graduate 'columbia_ma_'
    prefix — a math major keeps every undergraduate prerequisite."""
    from app.services.planner.prereq_graph import assumed_completed

    cat = {c: v for c, v in catalog.items()}
    assert assumed_completed(["columbia_math_major"], cat) == set()
    assert assumed_completed(["columbia_cc_core", "columbia_math_stat"], cat) == set()
    assert assumed_completed(["columbia_ma_philosophy"], cat) != set()
    assert assumed_completed(["columbia_ms_cs_ml"], cat) != set()
