from pathlib import Path

from app.services.sync.bulletin import parse_bulletin_courses, parse_courselists

FIXTURE = (Path(__file__).parent / "fixtures" / "bulletin_sample.html").read_text()


def test_parses_simple_course():
    courses = {c.code: c for c in parse_bulletin_courses(FIXTURE)}
    c = courses["COMS W1004"]
    assert c.subject == "COMS"
    assert c.number == "W1004"
    assert c.points_min == 3.0 and c.points_max == 3.0
    assert "general introduction" in c.description.lower()
    assert c.prereq_text == ""


def test_parses_point_range_and_prereq_text():
    courses = {c.code: c for c in parse_bulletin_courses(FIXTURE)}
    c = courses["COMS W3998"]
    assert c.points_min == 1.0 and c.points_max == 3.0
    assert c.prereq_text.startswith("Prerequisites: Approval")
    assert "Independent project" in c.description


def test_title_is_prettified_not_shouty():
    courses = {c.code: c for c in parse_bulletin_courses(FIXTURE)}
    assert courses["COMS W1004"].title == "Programming In Java"
    # Already-mixed-case titles pass through
    assert courses["COMS W4901"].title == "Projects in Computer Science"


def test_parses_courselists_with_headers():
    lists = parse_courselists(FIXTURE)
    assert len(lists) == 1
    assert lists[0]["header"].startswith("Calculus Requirement")
    assert lists[0]["codes"] == ["MATH UN1201", "MATH UN1205"]
