"""Merge Columbia Directory data into the local Course table.

The directory is authoritative for: credits, what's offered this term, and
who's teaching. The hand-curated seed remains authoritative for prereqs,
descriptions, categories, and career tags — fields the directory doesn't
provide.

This means a sync run never deletes curated metadata; it only:
  - upserts new courses we haven't seen before (with empty curated fields)
  - keeps the existing prereq/description/categories on courses we know
  - ensures the relevant season is in `offered_terms`
  - updates `credits` only if the directory disagrees (rare)
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

from sqlmodel import Session, select

from app.models.course import Course
from app.models.directory_sync import DirectorySync
from app.services.sync.columbia_directory import (
    DirectoryCourse,
    fetch_subject_term,
)

DEFAULT_SUBJECTS = ("COMS", "CSEE", "ECON", "MATH", "STAT", "IEOR")
DEFAULT_TTL = timedelta(hours=24)


def _term_to_season(term: str) -> str:
    if term.lower().startswith("fall"):
        return "Fall"
    if term.lower().startswith("spring"):
        return "Spring"
    if term.lower().startswith("summer"):
        return "Summer"
    return term


def sync_subject_term(
    subject: str,
    term: str,
    *,
    session: Session,
    fetcher=fetch_subject_term,
) -> DirectorySync:
    """Fetch the directory for one (subject, term) and merge it into the DB."""
    season = _term_to_season(term)
    record = DirectorySync(subject=subject.upper(), term=term, fetched_at=datetime.utcnow())
    try:
        parsed: list[DirectoryCourse] = fetcher(subject, term)
    except Exception as e:  # network / parse failure
        record.status = "error"
        record.error = str(e)[:240]
        session.add(record)
        session.commit()
        session.refresh(record)
        return record

    inserted = 0
    updated = 0
    skipped_zero_credit = 0
    for d in parsed:
        existing = session.get(Course, d.code)
        if existing:
            changed = False
            if season not in (existing.offered_terms or []):
                existing.offered_terms = [*(existing.offered_terms or []), season]
                changed = True
            if d.credits and d.credits != existing.credits:
                existing.credits = d.credits
                changed = True
            if changed:
                session.add(existing)
                updated += 1
        else:
            # Skip recitation / lab attachments — the directory marks them as
            # 0-point sections that pair with a parent lecture and shouldn't be
            # standalone planner candidates.
            if d.credits <= 0:
                skipped_zero_credit += 1
                continue
            session.add(
                Course(
                    code=d.code,
                    title=_pretty_title(d.title),
                    department=d.subject,
                    credits=d.credits,
                    description="",
                    workload_level=3,
                    offered_terms=[season],
                    prerequisites=[],
                    categories=[],
                    career_tags=[],
                )
            )
            inserted += 1

    record.status = "ok"
    record.courses_fetched = len(parsed)
    record.courses_inserted = inserted
    record.courses_updated = updated
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def sync_many(
    subjects: list[str] | None = None,
    term: str = "Fall2026",
    *,
    session: Session,
) -> list[DirectorySync]:
    """Sync each subject in `subjects` for `term`. Returns the DirectorySync rows."""
    subjects = subjects or list(DEFAULT_SUBJECTS)
    records: list[DirectorySync] = []
    for subj in subjects:
        records.append(sync_subject_term(subj, term, session=session))
    return records


def is_stale(
    subject: str,
    term: str,
    *,
    session: Session,
    ttl: timedelta = DEFAULT_TTL,
) -> bool:
    """Should we refetch (subject, term)?"""
    stmt = (
        select(DirectorySync)
        .where(DirectorySync.subject == subject.upper())
        .where(DirectorySync.term == term)
        .order_by(DirectorySync.fetched_at.desc())
    )
    last = session.exec(stmt).first()
    if last is None or last.status != "ok":
        return True
    return datetime.utcnow() - last.fetched_at > ttl


_ACRONYMS = {
    "AI", "ML", "NLP", "OS", "CS", "OOP", "UI", "UX", "API", "SQL", "GPU",
    "CPU", "IO", "HCI", "VR", "AR", "IR", "DB", "CV", "PL", "SE", "DS",
    "I", "II", "III", "IV",
}

# Words kept lowercase in Title Case (unless they open the title).
_SMALL_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on",
    "or", "the", "to", "via", "with",
}


def _pretty_title(s: str) -> str:
    """Directory titles are SHOUTY ALL-CAPS. Render them in Title Case while
    preserving common CS acronyms (AI, ML, NLP, SQL, ...) and keeping small
    words (of, and, in, ...) lowercase. Hyphen/slash-joined words are
    capitalized per part ("Intro-Comput Sci/Prog")."""

    def cap_core(core: str, first: bool) -> str:
        if core.upper() in _ACRONYMS:
            return core.upper()
        if not first and core.lower() in _SMALL_WORDS:
            return core.lower()
        return core.capitalize()

    def cap(word: str, first: bool) -> str:
        if not word:
            return word
        # Strip trailing punctuation we want to keep attached
        core = word.rstrip(",.;:")
        tail = word[len(core):]
        if not core:
            return word
        # Capitalize each alphabetic part around -, /, ( etc.
        parts = re.split(r"([^A-Za-z']+)", core)
        out = []
        for i, part in enumerate(parts):
            if part and re.match(r"[A-Za-z']", part):
                out.append(cap_core(part, first and i == 0))
            else:
                out.append(part)
        return "".join(out) + tail

    words = s.split()
    return " ".join(cap(w, i == 0) for i, w in enumerate(words))
