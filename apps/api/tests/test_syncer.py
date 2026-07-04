from pathlib import Path

from sqlmodel import select

from app.models.course import Course
from app.models.directory_sync import DirectorySync
from app.services.sync.columbia_directory import parse_subject_html
from app.services.sync.syncer import is_stale, sync_subject_term


FIXTURE = (Path(__file__).parent / "fixtures" / "coms_fall2026.html").read_text()


def _fixture_fetcher(subject: str, term: str):
    return parse_subject_html(FIXTURE, subject=subject.upper())


def test_sync_merges_into_existing_curated_course(session):
    # COMS W1004 is already in the curated seed with Fall + Spring + curated prereqs.
    pre_existing = session.get(Course, "COMS W1004")
    assert pre_existing is not None
    pre_offered = set(pre_existing.offered_terms)
    pre_prereqs = pre_existing.prerequisites
    pre_description = pre_existing.description

    record = sync_subject_term("COMS", "Fall2026", session=session, fetcher=_fixture_fetcher)
    assert record.status == "ok"
    assert record.courses_fetched == 4

    refreshed = session.get(Course, "COMS W1004")
    # Curated metadata preserved
    assert refreshed.prerequisites == pre_prereqs
    assert refreshed.description == pre_description
    # Offered terms still include Fall (curated had it already)
    assert "Fall" in refreshed.offered_terms
    # Existing seasons preserved
    assert pre_offered.issubset(set(refreshed.offered_terms))


def test_sync_inserts_new_courses_from_directory(session):
    # COMS W1002 / BC1014 / BC1016 are not in the curated seed.
    assert session.get(Course, "COMS W1002") is None
    assert session.get(Course, "COMS BC1014") is None
    record = sync_subject_term("COMS", "Fall2026", session=session, fetcher=_fixture_fetcher)
    assert record.courses_inserted >= 3

    w1002 = session.get(Course, "COMS W1002")
    assert w1002 is not None
    assert w1002.credits == 4.0
    assert "Fall" in w1002.offered_terms
    # Inserted rows have empty curated metadata
    assert w1002.prerequisites == []
    assert w1002.description == ""


def test_sync_status_recorded(session):
    sync_subject_term("COMS", "Fall2026", session=session, fetcher=_fixture_fetcher)
    rows = list(session.exec(select(DirectorySync)).all())
    assert len(rows) == 1
    assert rows[0].subject == "COMS"
    assert rows[0].term == "Fall2026"
    assert rows[0].status == "ok"


def test_is_stale_true_when_never_synced(session):
    assert is_stale("COMS", "Fall2026", session=session) is True


def test_is_stale_false_immediately_after_sync(session):
    sync_subject_term("COMS", "Fall2026", session=session, fetcher=_fixture_fetcher)
    assert is_stale("COMS", "Fall2026", session=session) is False


def test_sync_handles_fetch_error(session):
    def boom(subject, term):
        raise RuntimeError("network down")

    record = sync_subject_term("COMS", "Fall2026", session=session, fetcher=boom)
    assert record.status == "error"
    assert "network" in (record.error or "")


def test_pretty_title_handles_hyphens_slashes_and_small_words():
    from app.services.sync.syncer import _pretty_title

    assert _pretty_title("INTRO-COMPUT SCI/PROG IN JAVA") == "Intro-Comput Sci/Prog in Java"
    assert _pretty_title("ANALYSIS OF ALGORITHMS I") == "Analysis of Algorithms I"
    assert _pretty_title("MACHINE LEARNING FOR NLP") == "Machine Learning for NLP"
    assert _pretty_title("EARTH'S ENVIRONMENTAL SYSTEMS") == "Earth's Environmental Systems"
