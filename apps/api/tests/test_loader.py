import json
from pathlib import Path

from app.seed.loader import _number_int, build_catalog, derive_categories


def _write(dirpath: Path, name: str, payload: dict):
    dirpath.mkdir(parents=True, exist_ok=True)
    (dirpath / name).write_text(json.dumps(payload))


def _mini_snapshots(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    _write(data, "bulletin_cs.json", {
        "source_url": "https://bulletin.test/cs", "scraped_at": "2026-07-04T00:00:00Z",
        "error": None, "courselists": [],
        "courses": [
            {"code": "COMS W1004", "subject": "COMS", "number": "W1004",
             "title": "Bulletin Title", "points_min": 3.0, "points_max": 3.0,
             "description": "Bulletin description text that is long enough.",
             "prereq_text": ""},
            {"code": "COMS W9999", "subject": "COMS", "number": "W9999",
             "title": "Brand New Grad Course", "points_min": 3.0, "points_max": 3.0,
             "description": "A scraped course nobody curated.", "prereq_text": "Prerequisites: none."},
        ],
    })
    _write(data, "directory_Fall2026.json", {
        "term": "Fall2026", "scraped_at": "2026-07-04T00:00:00Z",
        "subjects": {"COMS": {"error": None, "courses": [
            {"code": "COMS W1004", "title": "SHOUTY", "credits": 3.0},
            {"code": "COMS W8888", "title": "DIR ONLY COURSE", "credits": 3.0},
        ]}},
    })
    return data


def test_curated_fields_win_and_are_never_overwritten(tmp_path):
    courses, prov = build_catalog(data_dir=_mini_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    c = by_code["COMS W1004"]
    curated_title = "Introduction to Computer Science and Programming in Java"
    assert c["title"] == curated_title            # curated beats bulletin
    assert c["prerequisites"] == []                # curated CNF kept
    assert "Fall" in c["offered_terms"]            # union with directory
    assert prov["COMS W1004"]["origin"] == "curated"


def test_uncurated_bulletin_course_inserted_with_provenance(tmp_path):
    courses, prov = build_catalog(data_dir=_mini_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    c = by_code["COMS W9999"]
    assert c["title"] == "Brand New Grad Course"
    assert c["description"].startswith("A scraped course")
    assert c["prerequisites"] == [] and c["workload_level"] == 3
    assert prov["COMS W9999"]["origin"] == "bulletin"
    assert prov["COMS W9999"]["source_url"] == "https://bulletin.test/cs"
    assert prov["COMS W9999"]["bulletin_prereq_text"] == "Prerequisites: none."


def test_directory_only_course_inserted_prettified(tmp_path):
    courses, prov = build_catalog(data_dir=_mini_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    c = by_code["COMS W8888"]
    assert c["title"] == "Dir Only Course"
    assert c["offered_terms"] == ["Fall"]
    assert prov["COMS W8888"]["origin"] == "directory"


def test_derived_categories():
    assert "cs_elective_eligible" in derive_categories("COMS W4771", "COMS", 4771, 3)
    assert "ms_grad_eligible" in derive_categories("COMS W4771", "COMS", 4771, 3)
    assert "econ_elective_3000" in derive_categories("ECON GU4280", "ECON", 4280, 3)
    assert derive_categories("COMS W1004", "COMS", 1004, 3) == []


def test_number_int_extraction_handles_letter_prefixes():
    # W1004 -> 1004, UN3211 -> 3211, E6998 -> 6998, BC1014 -> 1014
    assert _number_int("W1004") == 1004
    assert _number_int("UN3211") == 3211
    assert _number_int("E6998") == 6998
    assert _number_int("BC1014") == 1014
