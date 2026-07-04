from pathlib import Path

from app.services.sync.cs_pathways import normalize_codes, parse_pathway_page

FIXTURE = (Path(__file__).parent / "fixtures" / "ms_pathway_sample.html").read_text()


def test_sections_bounded_by_summary_and_program_planning():
    page = parse_pathway_page(FIXTURE)
    headings = [s["heading"] for s in page["sections"]]
    assert headings == ["1. Breadth Courses", "2. Fundamental Courses", "3. Secondary Courses"]


def test_rule_text_captured():
    page = parse_pathway_page(FIXTURE)
    fund = page["sections"][1]
    assert fund["rule_text"].startswith("Students complete two courses")


def test_group_column_and_or_groups():
    page = parse_pathway_page(FIXTURE)
    entries = page["sections"][1]["entries"]
    assert entries[0]["group"] == "A"
    assert entries[0]["codes"] == ["COMS W4252"]
    # OR-row: three alternatives, footnote marker stripped
    assert entries[1]["codes"] == ["COMS W4771", "COMS W4721", "ELEN E4720"]
    assert "[1]" not in entries[1]["raw"]
    # shorthand "COMS 4776" -> W-prefix at 4000-level
    assert entries[2]["codes"] == ["COMS W4776"]
    assert entries[3]["group"] == "B"


def test_table_without_group_column():
    page = parse_pathway_page(FIXTURE)
    entries = page["sections"][2]["entries"]
    assert entries[0]["group"] is None
    assert entries[0]["codes"] == ["COMS W4111"]
    # parenthesized alternative number
    assert entries[1]["codes"] == ["COMS W4772", "COMS E6772"]
    assert entries[1]["title"].startswith("Advanced Machine Learning")


def test_normalize_codes_heuristics():
    assert normalize_codes("COMS 6772") == ["COMS E6772"]
    assert normalize_codes("CSEE 4140") == ["CSEE E4140"]
    assert normalize_codes("COMS/CSEE W4119") == ["COMS W4119", "CSEE W4119"]
    assert normalize_codes("nonsense text") == []


def test_normalize_codes_ignores_years_and_loose_numbers():
    # "Spring 2018" must not become "COMS 2018"
    assert normalize_codes("COMS W4772 only valid if taken in Spring 2018") == ["COMS W4772"]
    # parenthesized and or-joined continuations still ride the subject
    assert normalize_codes("COMS W4772 (E6772)") == ["COMS W4772", "COMS E6772"]
    assert normalize_codes("COMS W4771 or 4721") == ["COMS W4771", "COMS W4721"]
