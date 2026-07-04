from pathlib import Path

from app.services.sync.columbia_directory import parse_subject_html


FIXTURE = Path(__file__).parent / "fixtures" / "coms_fall2026.html"


def test_parses_all_courses():
    html = FIXTURE.read_text()
    courses = parse_subject_html(html, subject="COMS")
    codes = [c.code for c in courses]
    assert codes == [
        "COMS W1002",
        "COMS W1004",
        "COMS BC1014",
        "COMS BC1016",
    ]


def test_w1004_has_two_sections_and_three_credits():
    html = FIXTURE.read_text()
    courses = parse_subject_html(html, subject="COMS")
    w1004 = next(c for c in courses if c.code == "COMS W1004")
    assert w1004.title == "INTRO-COMPUT SCI/PROG IN JAVA"
    assert w1004.credits == 3.0
    assert len(w1004.sections) == 2
    s1, s2 = w1004.sections
    assert s1.section == "001"
    assert s1.call_number == "13512"
    assert s1.instructor == "Paul S Blaer"
    assert s1.credits == 3.0
    assert s1.enrollment_current == 79
    assert s1.enrollment_max == 320
    assert s2.section == "002"
    assert s2.enrollment_current == 29


def test_w1002_credit_value_from_sections():
    html = FIXTURE.read_text()
    courses = parse_subject_html(html, subject="COMS")
    w1002 = next(c for c in courses if c.code == "COMS W1002")
    assert w1002.credits == 4.0
    assert len(w1002.sections) == 2
    # Section title variants are captured (Computing in Economics / Art)
    variants = {s.title_variant for s in w1002.sections}
    assert "COMPUTING IN ECONOMICS" in variants
    assert "COMPUTING IN ART" in variants


def test_bc1014_full_enrollment_parses():
    html = FIXTURE.read_text()
    courses = parse_subject_html(html, subject="COMS")
    bc1014 = next(c for c in courses if c.code == "COMS BC1014")
    sec = bc1014.sections[0]
    # "0 students as of May 29, 2026 / Full" → 0 current, no max in the string
    assert sec.enrollment_current == 0
    assert sec.enrollment_max is None


def test_missing_table_returns_empty():
    assert parse_subject_html("<html><body><p>nope</p></body></html>", subject="COMS") == []
