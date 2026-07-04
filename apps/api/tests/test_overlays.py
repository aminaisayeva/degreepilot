def test_curated_overlay_matches_legacy_list():
    from app.seed.courses import CS_AND_ECON_COURSES
    from app.seed.overlays import ALL_CURATED, CURATED

    assert ALL_CURATED == CS_AND_ECON_COURSES
    assert len(CURATED) == len(ALL_CURATED)  # no duplicate codes
    assert CURATED["COMS W1004"]["title"]


def test_every_curated_entry_has_required_fields():
    from app.seed.overlays import ALL_CURATED

    for spec in ALL_CURATED:
        for field in ("code", "title", "department", "credits", "offered_terms",
                      "prerequisites", "categories", "career_tags", "workload_level"):
            assert field in spec, f"{spec.get('code')} missing {field}"
