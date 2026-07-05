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


def _synth_snapshots(tmp_path: Path) -> Path:
    data = tmp_path / "data"
    _write(data, "bulletin_cs.json", {
        "source_url": "https://bulletin.test/cs", "scraped_at": "2026-07-04T00:00:00Z",
        "error": None,
        "courses": [],
        "courselists": [
            {"header": "", "section": "Area Foundation Courses (9 to 12 points):",
             "codes": ["CSOR E4231"], "titles": {"CSOR E4231": "ANALYSIS OF ALGORITHMS I"}},
        ],
    })
    _write(data, "bulletin_core_science.json", {
        "source_url": "https://bulletin.test/science", "scraped_at": "2026-07-04T00:00:00Z",
        "error": None,
        "courses": [],
        "courselists": [
            {"header": "Astronomy", "section": "Science B",
             "codes": ["ASTR UN1403", "EESC UN2100"],
             "titles": {"ASTR UN1403": "EARTH, MOON, AND PLANETS (*)",
                        "EESC UN2100": "EARTH'S ENVIRONMENTAL SYSTEMS"}},
            {"header": "Astronomy", "section": "Science C",
             "codes": ["EESC UN2100"],
             "titles": {"EESC UN2100": "EARTH'S ENVIRONMENTAL SYSTEMS"}},
            {"header": "Computer Science", "section": "Science C",
             "codes": ["COMS W1002"],
             "titles": {"COMS W1002": "COMPUTING IN CONTEXT"}},
        ],
    })
    return data


def test_adopted_list_codes_synthesized_with_titles(tmp_path):
    courses, prov = build_catalog(data_dir=_synth_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    c = by_code["CSOR E4231"]
    assert c["title"] == "Analysis of Algorithms I"
    assert c["department"] == "CSOR"
    assert prov["CSOR E4231"]["origin"] == "bulletin_list"
    assert prov["CSOR E4231"]["source_url"] == "https://bulletin.test/cs"


def test_approved_science_list_gets_category_even_for_curated(tmp_path):
    courses, _ = build_catalog(data_dir=_synth_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    # synthesized new course carries the mapped category
    assert "core_science" in by_code["EESC UN2100"]["categories"]
    # curated ASTR UN1403 keeps its curated category (already core_science)
    assert "core_science" in by_code["ASTR UN1403"]["categories"]
    # marker suffix "(*)" is stripped from synthesized titles
    assert by_code["EESC UN2100"]["title"] == "Earth's Environmental Systems"


def test_science_sections_map_to_a_b_c_categories(tmp_path):
    courses, _ = build_catalog(data_dir=_synth_snapshots(tmp_path))
    by_code = {c["code"]: c for c in courses}
    # Science B only
    assert "core_science_b" in by_code["ASTR UN1403"]["categories"]
    assert "core_science_c" not in by_code["ASTR UN1403"]["categories"]
    # On both lists → both categories
    assert "core_science_b" in by_code["EESC UN2100"]["categories"]
    assert "core_science_c" in by_code["EESC UN2100"]["categories"]
    # Science C only (CS course counting toward Science C)
    assert "core_science_c" in by_code["COMS W1002"]["categories"]
    assert "core_science_b" not in by_code["COMS W1002"]["categories"]
    # Science A = Frontiers, tagged in the curated overlay
    assert "core_science_a" in by_code["SCNC CC1000"]["categories"]


def test_pathway_listed_codes_synthesized(tmp_path):
    data = _synth_snapshots(tmp_path)
    _write(data, "ms_pathways.json", {
        "scraped_at": "2026-07-04T00:00:00Z",
        "pathways": {
            "ml": {
                "source_url": "https://cs.test/ms/ml", "title": "Machine Learning",
                "error": None,
                "sections": [{
                    "heading": "2. Fundamental Courses", "rule_text": "…",
                    "entries": [
                        {"group": "A", "raw": "ELEN 4720",
                         "codes": ["ELEN E4720"],
                         "title": "Machine Learning for Signals, Information and Data"},
                        {"group": "A", "raw": "COMS W4771",
                         "codes": ["COMS W4771"], "title": "Machine Learning"},
                    ],
                }],
            },
        },
    })
    courses, prov = build_catalog(data_dir=data)
    by_code = {c["code"]: c for c in courses}
    c = by_code["ELEN E4720"]
    assert c["title"] == "Machine Learning for Signals, Information and Data"
    assert c["department"] == "ELEN"
    assert prov["ELEN E4720"]["origin"] == "pathway_list"
    assert prov["ELEN E4720"]["source_url"] == "https://cs.test/ms/ml"
    # curated code on a pathway list is untouched
    assert prov["COMS W4771"]["origin"] == "curated"


def test_derived_categories():
    assert "cs_elective_eligible" in derive_categories("COMS W4771", "COMS", 4771, 3)
    assert "ms_grad_eligible" in derive_categories("COMS W4771", "COMS", 4771, 3)
    assert "econ_elective_3000" in derive_categories("ECON GU4280", "ECON", 4280, 3)
    assert derive_categories("COMS W1004", "COMS", 1004, 3) == []


def test_barnard_sections_not_auto_derived():
    # Barnard (BC-numbered) courses never auto-qualify for CC/SEAS electives;
    # curation must opt them in explicitly.
    assert derive_categories("ECON BC3011", "ECON", 3011, 3) == []
    assert derive_categories("COMS BC3420", "COMS", 3420, 3) == []


def test_number_int_extraction_handles_letter_prefixes():
    # W1004 -> 1004, UN3211 -> 3211, E6998 -> 6998, BC1014 -> 1014
    assert _number_int("W1004") == 1004
    assert _number_int("UN3211") == 3211
    assert _number_int("E6998") == 6998
    assert _number_int("BC1014") == 1014


def test_econ_electives_exclude_graduate_gr_level():
    # ECON GR5xxx are graduate-school-only; undergrad electives cap at 4999.
    assert derive_categories("ECON GR5211", "ECON", 5211, 3) == []
    assert "econ_elective_3000" in derive_categories("ECON GU4280", "ECON", 4280, 3)
    assert "econ_elective_3000" in derive_categories("ECON UN3025", "ECON", 3025, 4)


def test_topics_sections_become_distinct_courses(tmp_path):
    data = _mini_snapshots(tmp_path)
    _write(data, "directory_Spring2027.json", {
        "term": "Spring2027", "scraped_at": "2026-07-05T00:00:00Z",
        "subjects": {"COMS": {"error": None, "courses": [
            {"code": "COMS W4995", "title": "TOPICS IN COMPUTER SCIENCE", "credits": 3.0,
             "topics": [
                 {"section": "001", "title": "SCIENCE OF BLOCKCHAINS", "credits": 3.0,
                  "instructor": "A Prof"},
                 {"section": "002", "title": "DEEP LRNG FOR COMP VISION", "credits": 3.0,
                  "instructor": "B Prof"},
             ]},
        ]}},
    })
    courses, prov = build_catalog(data_dir=data)
    by_code = {c["code"]: c for c in courses}
    topic_codes = [c for c in by_code if c.startswith("COMS W4995-")]
    assert len(topic_codes) == 2
    blockchains = next(c for c in topic_codes
                       if by_code[c]["title"] == "Science of Blockchains")
    assert by_code[blockchains]["offered_terms"] == ["Spring"]
    assert "A Prof" in by_code[blockchains]["description"]
    assert prov[blockchains]["origin"] == "directory_topic"
    # Umbrella stays and points readers at the topic entries.
    assert "COMS W4995" in by_code
    assert "individual topic sections" in by_code["COMS W4995"]["description"]


def test_breadth_categories_follow_number_patterns():
    # cs.columbia.edu breadth chart: Systems = COMS 41xx (minus 4121/416x/417x),
    # 48xx, 4444, listed CSEE + EECS 4340; Theory = COMS 42xx + CSOR 4231/4223;
    # AI = COMS 47xx (minus 4721/4726) + 416x/417x + CBMF 4761.
    assert "ms_breadth_systems" in derive_categories("COMS W4118", "COMS", 4118, 3)
    assert "ms_breadth_systems" in derive_categories("COMS W4111", "COMS", 4111, 3)
    assert "ms_breadth_systems" in derive_categories("COMS W4156", "COMS", 4156, 3)
    assert "ms_breadth_systems" not in derive_categories("COMS W4121", "COMS", 4121, 3)
    assert "ms_breadth_systems" in derive_categories("CSEE W4119", "CSEE", 4119, 3)
    assert "ms_breadth_systems" in derive_categories("COMS W4444", "COMS", 4444, 3)
    assert "ms_breadth_theory" in derive_categories("COMS W4231", "COMS", 4231, 3)
    assert "ms_breadth_theory" in derive_categories("CSOR E4231", "CSOR", 4231, 3)
    assert "ms_breadth_theory" not in derive_categories("CSOR W4246", "CSOR", 4246, 3)
    assert "ms_breadth_ai" in derive_categories("COMS W4771", "COMS", 4771, 3)
    assert "ms_breadth_ai" not in derive_categories("COMS W4721", "COMS", 4721, 3)
    assert "ms_breadth_ai" in derive_categories("COMS W4170", "COMS", 4170, 3)
    assert "ms_breadth_systems" not in derive_categories("COMS W4170", "COMS", 4170, 3)
    assert "ms_breadth_ai" in derive_categories("CBMF W4761", "CBMF", 4761, 3)


def test_administrative_codes_are_not_elective_eligible():
    # Fieldwork / CPT / projects / independent-study codes are not academic
    # electives and must not be auto-derived as eligible.
    for num in (3998, 4901, 4910, 6910):
        code = f"COMS W{num}" if num < 6000 else f"COMS E{num}"
        assert derive_categories(code, "COMS", num, 3) == [], code
    # regular courses unaffected
    assert "ms_grad_eligible" in derive_categories("COMS E6111", "COMS", 6111, 3)
