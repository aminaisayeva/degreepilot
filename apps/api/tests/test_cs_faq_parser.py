from pathlib import Path

from app.services.sync.cs_faq import parse_faq_page

FIXTURE = (Path(__file__).parent / "fixtures" / "ms_faq_sample.html").read_text()


def test_parses_accordion_qa_pairs():
    entries = parse_faq_page(FIXTURE)
    assert len(entries) == 2
    assert entries[0]["question"] == "What are the overall requirements of the program?"
    assert "must still complete 30 points" in entries[0]["answer"]
    assert "breadth requirement page" in entries[0]["answer"]
    assert entries[1]["question"] == "Can I write a thesis?"
    assert entries[1]["answer"].startswith("Only in the MS Thesis pathway")
