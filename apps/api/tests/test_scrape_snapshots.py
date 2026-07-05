import json

from scripts.scrape_catalog import bulletin_snapshot, directory_snapshot, write_snapshot
from app.services.sync.bulletin import BulletinCourse
from app.services.sync.columbia_directory import DirectoryCourse


def test_bulletin_snapshot_shape(tmp_path):
    snap = bulletin_snapshot(
        source_url="https://example.test/cs",
        courses=[BulletinCourse(code="COMS W1004", subject="COMS", number="W1004",
                                title="Programming In Java", points_min=3, points_max=3)],
        courselists=[{"header": "Intro", "codes": ["COMS W1004"]}],
        scraped_at="2026-07-04T00:00:00Z",
    )
    path = write_snapshot(snap, tmp_path / "bulletin_cs.json")
    data = json.loads(path.read_text())
    assert data["source_url"] == "https://example.test/cs"
    assert data["courses"][0]["code"] == "COMS W1004"
    assert data["courselists"][0]["codes"] == ["COMS W1004"]
    assert data["error"] is None


def test_directory_snapshot_shape(tmp_path):
    snap = directory_snapshot(
        term="Fall2026",
        subjects={"COMS": {"courses": [DirectoryCourse(subject="COMS", number="W1004",
                                                       title="X", credits=3.0)], "error": None}},
        scraped_at="2026-07-04T00:00:00Z",
    )
    path = write_snapshot(snap, tmp_path / "directory_Fall2026.json")
    data = json.loads(path.read_text())
    assert data["subjects"]["COMS"]["courses"][0]["code"] == "COMS W1004"
    assert data["subjects"]["COMS"]["courses"][0]["credits"] == 3.0


def test_directory_snapshot_records_topics_sections(tmp_path):
    from app.services.sync.columbia_directory import DirectorySection

    umbrella = DirectoryCourse(
        subject="COMS", number="W4995", title="TOPICS IN COMPUTER SCIENCE", credits=3.0,
        sections=[
            DirectorySection(section="001", call_number="11111",
                             title_variant="TOPICS: LARGE LANGUAGE MODELS",
                             instructor="A Prof", credits=3.0),
            DirectorySection(section="002", call_number="22222",
                             title_variant="TOPICS: CLOUD COMPUTING",
                             instructor="B Prof", credits=3.0),
        ],
    )
    snap = directory_snapshot(
        term="Fall2026",
        subjects={"COMS": {"courses": [umbrella], "error": None}},
        scraped_at="2026-07-05T00:00:00Z",
    )
    entry = snap["subjects"]["COMS"]["courses"][0]
    assert entry["code"] == "COMS W4995"
    topics = entry["topics"]
    assert len(topics) == 2
    assert topics[0] == {"section": "001", "title": "TOPICS: LARGE LANGUAGE MODELS",
                         "credits": 3.0, "instructor": "A Prof"}
