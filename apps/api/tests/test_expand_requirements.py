import pytest

from app.seed.expand import expand_dynamic_requirements, validate_catalog

CATALOG = [
    {"code": "COMS W3134", "categories": ["cs_elective_eligible"]},
    {"code": "COMS W4771", "categories": ["cs_elective_eligible", "ms_grad_eligible"]},
    {"code": "COMS W1004", "categories": []},
]


def test_dynamic_replaced_and_marker_stripped():
    programs = {"p": [{"name": "Electives", "type": "n_of",
                       "courses": [], "_dynamic": "cs_elective_eligible"}]}
    out = expand_dynamic_requirements(programs, CATALOG)
    req = out["p"][0]
    assert req["courses"] == ["COMS W3134", "COMS W4771"]
    assert "_dynamic" not in req
    # input untouched
    assert programs["p"][0]["_dynamic"] == "cs_elective_eligible"


def test_hand_listed_codes_kept_first():
    programs = {"p": [{"name": "Electives", "type": "n_of",
                       "courses": ["COMS W4771"], "_dynamic": "cs_elective_eligible"}]}
    out = expand_dynamic_requirements(programs, CATALOG)
    assert out["p"][0]["courses"] == ["COMS W4771", "COMS W3134"]


def test_validate_catalog_names_missing_codes():
    programs = {"p": [{"name": "Ghost req", "type": "all_of", "courses": ["FAKE X0000"]}]}
    with pytest.raises(ValueError) as e:
        validate_catalog(CATALOG, programs)
    assert "FAKE X0000" in str(e.value)
    assert "Ghost req" in str(e.value)


def test_validate_catalog_passes_on_good_data():
    programs = {"p": [{"name": "ok", "type": "all_of", "courses": ["COMS W1004"]}]}
    validate_catalog(CATALOG, programs)  # no raise
