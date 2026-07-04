"""Parse MS pathway pages from cs.columbia.edu/education/ms/<slug>/.

Pages are WordPress content: an h2 "SUMMARY OF REQUIREMENTS", numbered h3
sections ("2. Fundamental Courses"), rule paragraphs, and plain bordered
tables with (optional Group | Course ID | Title) columns. Requirements end at
the "PROGRAM PLANNING" heading.

Course ID cells are messy: "COMS W4771 or COMS W4721 or ELEN 4720",
"COMS W4772 (E6772)", "COMS/CSEE W4119", footnote sups. We keep the cleaned
raw text for human verification and extract best-effort canonical codes.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

_SECTION_RE = re.compile(r"^\d+\.\s+\S")
_FOOTNOTE_RE = re.compile(r"\[\d+\]")
# Explicit code: subject + optional letter prefix + 4-digit number
_CODE_RE = re.compile(r"\b([A-Z]{2,4})\s+([A-Z]{0,2})(\d{4})\b")
# Bare number continuation after a subject — only when introduced by an
# alternative marker ("(", "/", "or") so prose years ("Spring 2018") don't
# parse as course numbers.
_NUM_RE = re.compile(r"(?:\(|/|\bor\s+)\s*([A-Z]{0,2})(\d{4})\b")

# SEAS departments list courses with an E prefix; COMS is W at 4000-level and
# E at 6000-level. Used only when the page omits the prefix.
_SEAS_SUBJECTS = {"ELEN", "CSEE", "CSOR", "EECS", "IEOR", "CBMF", "BMEN", "EAEE", "ECBM"}


def _guess_prefix(subject: str, number: str) -> str:
    if subject == "COMS":
        return "E" if number.startswith("6") else "W"
    if subject in _SEAS_SUBJECTS:
        return "E"
    return ""


def _clean(s: str) -> str:
    s = s.replace("\xa0", " ").replace("​", "")
    s = _FOOTNOTE_RE.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def normalize_codes(raw: str) -> list[str]:
    """Extract canonical codes from a Course ID cell.

    Handles: multiple subjects ("COMS/CSEE W4119"), missing letter prefixes
    ("COMS 4776" → W, "ELEN 4720" → E), parenthesized alternative numbers
    ("COMS W4772 (E6772)"), and "or"-joined alternatives.
    """
    text = _clean(raw)
    out: list[str] = []

    # Expand "SUBJ1/SUBJ2 <code>" into both subjects.
    text = re.sub(
        r"\b([A-Z]{2,4})/([A-Z]{2,4})\s+([A-Z]{0,2}\d{4})\b",
        r"\1 \3 \2 \3",
        text,
    )

    last_subject: str | None = None
    pos = 0
    while pos < len(text):
        m = _CODE_RE.search(text, pos)
        n = _NUM_RE.search(text, pos)
        # Prefer an explicit subject+number match at the nearest position.
        if m and (not n or m.start() <= n.start()):
            subject, prefix, number = m.group(1), m.group(2), m.group(3)
            last_subject = subject
            pos = m.end()
        elif n and last_subject:
            # Bare number (or prefixed number) rides on the last subject:
            # "COMS W4772 (E6772)" / "G6509/6701".
            subject, prefix, number = last_subject, n.group(1), n.group(2)
            pos = n.end()
        else:
            break
        prefix = prefix or _guess_prefix(subject, number)
        code = f"{subject} {prefix}{number}"
        if code not in out:
            out.append(code)
    return out


def _parse_table(table: Tag) -> list[dict]:
    rows = table.find_all("tr")
    if not rows:
        return []
    header = [_clean(td.get_text(" ", strip=True)).lower() for td in rows[0].find_all(["td", "th"])]
    has_group = bool(header) and header[0].startswith("group")
    id_col = 1 if has_group else 0
    title_col = id_col + 1

    entries: list[dict] = []
    for tr in rows[1:]:
        cells = tr.find_all(["td", "th"])
        if len(cells) <= id_col:
            continue
        raw = _clean(cells[id_col].get_text(" ", strip=True))
        if not raw:
            continue
        codes = normalize_codes(raw)
        if not codes:
            continue
        title = _clean(cells[title_col].get_text(" ", strip=True)) if len(cells) > title_col else ""
        group = _clean(cells[0].get_text(" ", strip=True)) if has_group else None
        entries.append({"group": group or None, "raw": raw, "codes": codes, "title": title})
    return entries


def parse_pathway_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    title = _clean(h1.get_text(" ", strip=True)) if isinstance(h1, Tag) else ""

    sections: list[dict] = []
    current: dict | None = None
    started = False

    for el in soup.find_all(["h2", "h3", "p", "table"]):
        text = _clean(el.get_text(" ", strip=True)) if el.name != "table" else ""
        if el.name == "h2":
            if text.upper().startswith("SUMMARY OF REQUIREMENTS"):
                started = True
                continue
            if started and text.upper().startswith("PROGRAM PLANNING"):
                break
            continue
        if el.name == "h3":
            if _SECTION_RE.match(text):
                started = True
                current = {"heading": text, "rule_text": "", "entries": []}
                sections.append(current)
            elif started and current is not None and not _SECTION_RE.match(text):
                # Non-numbered h3 after requirements started (e.g. sidebar
                # "Upcoming Events") — stop collecting into sections.
                current = None
            continue
        if not started or current is None:
            continue
        if el.name == "p":
            if text and not current["entries"]:
                current["rule_text"] = (current["rule_text"] + " " + text).strip()
            continue
        if el.name == "table":
            current["entries"].extend(_parse_table(el))

    return {"title": title, "sections": sections}
