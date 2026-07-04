"""Academic-term utilities.

Terms in DegreePilot are represented as `"Fall 2025"`, `"Spring 2026"`, etc.
We support Fall, Spring, and (optionally) Summer.
"""

from __future__ import annotations

TERM_ORDER = {"Spring": 0, "Summer": 1, "Fall": 2}
SEASONS_DEFAULT = ("Fall", "Spring")


def parse_term(term: str) -> tuple[str, int]:
    """`"Fall 2025"` → `("Fall", 2025)`. Normalizes case; raises ValueError on garbage."""
    parts = (term or "").strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError(f"Invalid term {term!r} — expected e.g. 'Fall 2025'")
    season = parts[0].capitalize()
    if season not in TERM_ORDER:
        raise ValueError(f"Invalid term {term!r} — season must be one of {sorted(TERM_ORDER)}")
    return season, int(parts[1])


def format_term(season: str, year: int) -> str:
    return f"{season} {year}"


def next_term(term: str, *, seasons: tuple[str, ...] = SEASONS_DEFAULT) -> str:
    """Return the next term in the academic sequence, respecting allowed seasons.

    Seasons outside `seasons` (e.g. "Summer 2025" with Fall/Spring only) advance
    to the next allowed season later in the same calendar year, never backwards.
    """
    season, year = parse_term(term)
    ordered = sorted(seasons, key=lambda s: TERM_ORDER[s])
    current = TERM_ORDER[season]
    for s in ordered:
        if TERM_ORDER[s] > current:
            return format_term(s, year)
    # rolled over to a new academic year
    return format_term(ordered[0], year + 1)


def terms_between(start_term: str, end_term: str, *, seasons: tuple[str, ...] = SEASONS_DEFAULT) -> list[str]:
    """Inclusive list of terms from start to end."""
    out = [start_term]
    cursor = start_term
    # safety cap
    for _ in range(40):
        if cursor == end_term:
            break
        cursor = next_term(cursor, seasons=seasons)
        out.append(cursor)
        if _term_index(cursor) > _term_index(end_term):
            break
    if out[-1] != end_term and _term_index(out[-1]) > _term_index(end_term):
        out.pop()
    return out


def _term_index(term: str) -> int:
    season, year = parse_term(term)
    return year * 10 + TERM_ORDER.get(season, 0)
