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
