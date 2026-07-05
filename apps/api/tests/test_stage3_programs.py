from app.models.requirement import RequirementType
from app.seed.requirements import PROGRAM_LABELS, PROGRAMS


def _reqs(slug):
    return PROGRAMS[slug]


def test_stage3_programs_registered():
    for slug in ("columbia_econ_major", "columbia_ai_minor",
                 "columbia_data_science_major", "columbia_cs_concentration"):
        assert slug in PROGRAMS and slug in PROGRAM_LABELS


def test_econ_major_structure():
    reqs = {r["name"]: r for r in _reqs("columbia_econ_major")}
    core = reqs["Economics Core"]
    assert core["type"] == RequirementType.ALL_OF
    assert core["courses"] == ["ECON UN1105", "ECON UN3211", "ECON UN3213", "ECON UN3412"]
    electives = reqs["Economics Electives (pick 5)"]
    assert electives["_dynamic"] == "econ_elective_3000"
    assert electives["count_required"] == 5
    seminar = reqs["Economics Seminar (pick 1)"]
    assert seminar["count_required"] == 1
    assert "ECON GU4321" in seminar["courses"]


def test_ai_minor_is_six_courses():
    reqs = _reqs("columbia_ai_minor")
    # 6 cards ↔ 6 courses per the bulletin
    assert len(reqs) == 6
    by_name = {r["name"]: r for r in reqs}
    assert by_name["AI Requirement"]["courses"] == ["COMS W4701"]
    assert by_name["Intro Computing"]["type"] == RequirementType.ONE_OF
    assert set(by_name["Intro Computing"]["courses"]) == {"ENGI E1006", "COMS W1002"}
    assert by_name["AI Elective (pick 1)"]["count_required"] == 1
    assert "ELEN E4720" in by_name["AI Elective (pick 1)"]["courses"]


def test_data_science_major_structure():
    by_name = {r["name"]: r for r in _reqs("columbia_data_science_major")}
    assert by_name["Prerequisites"]["type"] == RequirementType.ALL_OF
    assert "STAT UN1201" in by_name["Prerequisites"]["courses"]
    assert set(by_name["Machine Learning"]["courses"]) == {"STAT GU4241", "COMS W4771"}
    assert by_name["Electives (pick 5)"]["count_required"] == 5


def test_cs_concentration_structure():
    by_name = {r["name"]: r for r in _reqs("columbia_cs_concentration")}
    assert set(by_name["Introduction to Computer Science"]["courses"]) == {"COMS W1004", "COMS W1007"}
    assert set(by_name["Data Structures"]["courses"]) == {"COMS W3134", "COMS W3137"}
    assert "STAT GU4001" in by_name["Math / Probability (pick 1)"]["courses"]


def test_all_stage3_codes_resolve_in_full_catalog():
    from app.seed.expand import expand_dynamic_requirements, validate_catalog
    from app.seed.loader import build_catalog

    catalog, _ = build_catalog()
    subset = {slug: PROGRAMS[slug] for slug in (
        "columbia_econ_major", "columbia_ai_minor",
        "columbia_data_science_major", "columbia_cs_concentration")}
    validate_catalog(catalog, expand_dynamic_requirements(subset, catalog))
