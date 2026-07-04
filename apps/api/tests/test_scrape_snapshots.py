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
