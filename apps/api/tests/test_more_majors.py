from app.models.requirement import RequirementType
from app.seed.requirements import PROGRAM_LABELS, PROGRAMS

EXPECTED = [
    "columbia_econ_financial", "columbia_econ_math", "columbia_econ_polisci",
    "columbia_econ_stat", "columbia_econ_philosophy",
    "columbia_math_major", "columbia_math_concentration", "columbia_applied_math_major",
    "columbia_math_minor", "columbia_math_prob_minor", "columbia_cs_math",
    "columbia_math_stat",
    "columbia_sustdev_major", "columbia_sustdev_concentration",
    "columbia_phil_major", "columbia_phil_concentration", "columbia_ma_philosophy",
    "columbia_english_major", "columbia_english_concentration",
]


def test_all_new_programs_registered():
    for slug in EXPECTED:
        assert slug in PROGRAMS and slug in PROGRAM_LABELS, slug


def test_econ_joints_share_the_core():
    for slug in ("columbia_econ_financial", "columbia_econ_math",
                 "columbia_econ_stat", "columbia_econ_philosophy"):
        core = next(r for r in PROGRAMS[slug] if r["name"] == "Economics Core")
        assert core["courses"] == ["ECON UN1105", "ECON UN3211", "ECON UN3213", "ECON UN3412"], slug


def test_phil_major_structure():
    by_name = {r["name"]: r for r in PROGRAMS["columbia_phil_major"]}
    assert by_name["Majors Seminar"]["courses"] == ["PHIL UN3912"]
    pts = by_name["Philosophy Coursework (30 points)"]
    assert pts["type"] == RequirementType.CATEGORY_CREDITS
    assert pts["category"] == "phil_ug"
    assert pts["credits_required"] == 30


def test_ma_philosophy_is_graduate_and_flagged_curated():
    reqs = PROGRAMS["columbia_ma_philosophy"]
    pts = next(r for r in reqs if r["type"] == RequirementType.CATEGORY_CREDITS)
    assert pts["category"] == "phil_grad"
    assert pts["credits_required"] == 30
    assert "verify" in pts["notes"].lower()
    # graduate prefix so waivers/pools apply
    assert "columbia_ma_philosophy".startswith("columbia_ma")


def test_sustdev_major_has_practicum_and_capstone():
    names = [r["name"] for r in PROGRAMS["columbia_sustdev_major"]]
    assert any("Practicum" in n for n in names)
    assert any("Capstone" in n for n in names)


def test_english_major_intro_uses_catalog_codes():
    by_name = {r["name"]: r for r in PROGRAMS["columbia_english_major"]}
    intro = by_name["Introductory Course"]
    assert set(intro["courses"]) == {"ENGL UN2000", "ENGL UN2001"}
    lit = by_name["Literature Coursework (10 courses)"]
    assert lit["category"] == "english_lit"
    assert "pre-1800" in lit["notes"]


def test_all_new_program_codes_resolve_in_full_catalog():
    from app.seed.expand import expand_dynamic_requirements, validate_catalog
    from app.seed.loader import build_catalog

    catalog, _ = build_catalog()
    subset = {slug: PROGRAMS[slug] for slug in EXPECTED}
    validate_catalog(catalog, expand_dynamic_requirements(subset, catalog))
