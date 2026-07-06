from app.seed.requirements import MS_CS_REQS
from app.seed.requirements_ms_tracks import TRACK_LABELS, build_track_programs


def test_ten_track_programs_built():
    programs = build_track_programs(MS_CS_REQS)
    assert set(programs) == set(TRACK_LABELS)
    assert len(programs) == 10
    for slug, reqs in programs.items():
        names = [r["name"] for r in reqs]
        # every track shares the three breadth cards and a total-points card
        assert sum(1 for n in names if n.startswith("Breadth:")) == 3, slug
        assert any(n.startswith("Total") for n in names), slug


def test_ml_track_fundamentals():
    programs = build_track_programs(MS_CS_REQS)
    ml = programs["columbia_ms_cs_ml"]
    fund = next(r for r in ml if "Fundamental" in r["name"])
    assert fund["count_required"] == 2
    assert "COMS W4771" in fund["courses"]
    assert "ELEN E4720" in fund["courses"]
    # exact scraped rule text is preserved for the UI / accuracy dashboard
    assert "group A" in fund["notes"]


def test_networks_secondary_pick_4():
    programs = build_track_programs(MS_CS_REQS)
    nw = programs["columbia_ms_cs_networks"]
    sec = next(r for r in nw if "Secondary" in r["name"])
    assert sec["count_required"] == 4
    assert sec["credits_required"] == 12
    assert "6000-level" in sec["notes"]


def test_thesis_track_has_e6902_and_grad_electives():
    programs = build_track_programs(MS_CS_REQS)
    th = programs["columbia_ms_cs_thesis"]
    thesis_card = next(r for r in th if "Thesis" in r["name"] and "Defense" not in r["name"])
    assert thesis_card["courses"] == ["COMS E6902"]
    assert thesis_card["credits_required"] == 9
    sec = next(r for r in th if "Secondary" in r["name"])
    assert sec["type"].value == "category_credits"
    assert sec["category"] == "ms_grad_eligible"
    assert sec["credits_required"] == 9


def test_all_referenced_codes_resolve_in_full_catalog():
    from app.seed.expand import validate_catalog
    from app.seed.loader import build_catalog

    catalog, _ = build_catalog()
    programs = build_track_programs(MS_CS_REQS)
    validate_catalog(catalog, programs)  # raises on any missing code


def test_ml_fundamentals_enforce_group_a():
    """'Two courses: both from A, or one A + one B (≥1 from A)' — encoded as
    the pick-2 union card PLUS a Group-A pick-1 card, so two Group-B courses
    (e.g. W4705 + W4701) no longer satisfy the fundamentals."""
    programs = build_track_programs(MS_CS_REQS)
    ml = programs["columbia_ms_cs_ml"]
    group_a = next(r for r in ml if "Group A" in r["name"])
    assert group_a["count_required"] == 1
    assert "COMS W4252" in group_a["courses"]
    assert "COMS W4771" in group_a["courses"]
    # Group-B-only courses must NOT be in the Group A card
    assert "COMS W4705" not in group_a["courses"]
    assert "COMS W4701" not in group_a["courses"]


def test_ml_group_a_audit_behavior(session, catalog):
    from app.models.requirement import Requirement
    from app.models.student import Student
    from app.services.audit.auditor import audit_student

    programs = build_track_programs(MS_CS_REQS)
    reqs = [Requirement(id=i, program="columbia_ms_cs_ml", **{k: v for k, v in r.items()})
            for i, r in enumerate(programs["columbia_ms_cs_ml"], start=1)]
    student = Student(id=9, name="T", current_term="Fall 2026", graduation_term="Spring 2028",
                      programs=["columbia_ms_cs_ml"],
                      waived_courses=["COMS W4705", "COMS W4701"])  # both Group B
    report = audit_student(student, "columbia_ms_cs_ml", reqs, catalog)
    by_name = {r.name: r for r in report.requirements}
    group_a = next(v for k, v in by_name.items() if "Group A" in k)
    assert group_a.satisfied is False


def test_tracks_have_6000_level_card():
    programs = build_track_programs(MS_CS_REQS)
    for slug in ("columbia_ms_cs_ml", "columbia_ms_cs_security"):
        card = next(r for r in programs[slug] if r["name"].startswith("6000-level Technical"))
        assert card["category"] == "ms_6000_technical"
        assert card["credits_required"] == 6
    total = next(r for r in programs["columbia_ms_cs_ml"] if r["name"].startswith("Total"))
    assert "PDL" in total["notes"] and "2.7" in total["notes"]


def test_secondary_6000_level_floor_cards():
    programs = build_track_programs(MS_CS_REQS)
    ml_floor = next(r for r in programs["columbia_ms_cs_ml"] if "6000-level (pick" in r["name"])
    assert ml_floor["count_required"] == 1
    assert all(int(c.split()[-1][-4:]) >= 6000 for c in ml_floor["courses"])
    nw_floor = next(r for r in programs["columbia_ms_cs_networks"] if "6000-level (pick" in r["name"])
    assert nw_floor["count_required"] == 2
