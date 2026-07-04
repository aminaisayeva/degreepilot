"""Parse the Columbia Directory of Classes.

Pages look like:
  https://doc.sis.columbia.edu/subj/COMS/_Fall2026.html

The HTML is deeply regular — one `<table class="course-listing">` containing
alternating `<th colspan=2>` "header" rows (one per course) and `<tr>` "section"
rows. Headers carry the canonical course code + title; sections carry call
number, credits, instructor, and enrollment.

The directory does NOT publish prerequisites or full descriptions — only the
live offering. Curated bulletin metadata in `app/seed/courses.py` remains
authoritative for those fields; the syncer only merges the live bits in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup, Tag

DOC_BASE = "https://doc.sis.columbia.edu/subj/{subject}/_{term}.html"
_USER_AGENT = "DegreePilot/0.1 (academic project; contact: aminaisayeva@degreepilot.dev)"


@dataclass
class DirectorySection:
    section: str
    call_number: str
    title_variant: str | None = None
    instructor: str | None = None
    credits: float = 0.0
    enrollment_current: int = 0
    enrollment_max: int | None = None


@dataclass
class DirectoryCourse:
    subject: str
    number: str  # e.g. "W1004", "BC1014"
    title: str
    credits: float = 0.0
    sections: list[DirectorySection] = field(default_factory=list)

    @property
    def code(self) -> str:
        return f"{self.subject} {self.number}"


def fetch_subject_term(
    subject: str,
    term: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = 20.0,
) -> list[DirectoryCourse]:
    """Fetch and parse the directory page for a given subject + term.

    `term` is the URL form Columbia uses: "Fall2026", "Spring2027", etc.
    """
    url = DOC_BASE.format(subject=subject.upper(), term=term)
    own_client = client is None
    c = client or httpx.Client(timeout=timeout, headers={"User-Agent": _USER_AGENT})
    try:
        r = c.get(url)
        r.raise_for_status()
        return parse_subject_html(r.text, subject=subject.upper())
    finally:
        if own_client:
            c.close()


def parse_subject_html(html: str, *, subject: str) -> list[DirectoryCourse]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="course-listing")
    if not isinstance(table, Tag):
        return []

    courses: list[DirectoryCourse] = []
    current: DirectoryCourse | None = None

    for tr in table.find_all("tr"):
        # New course header row
        th = tr.find("th", attrs={"colspan": "2"})
        if isinstance(th, Tag):
            current = _parse_course_header(th, subject=subject)
            if current is not None:
                courses.append(current)
            continue
        if current is None:
            continue

        # Section row
        section = _parse_section_row(tr)
        if section is None:
            continue
        current.sections.append(section)
        if section.credits and section.credits > current.credits:
            current.credits = section.credits

    return courses


def _parse_course_header(th: Tag, *, subject: str) -> DirectoryCourse | None:
    """Header looks like:
       'Fall 2026 Computer Science W1004<br>INTRO-COMPUT SCI/PROG IN JAVA'
    """
    # Replace <br> with a sentinel so we can split into header + title
    raw = th.get_text(separator="|").strip()
    parts = [p.strip() for p in raw.split("|", 1)]
    if len(parts) != 2:
        return None
    header, title = parts

    # Last token of the header is the course number (e.g. "W1004", "BC1014").
    tokens = header.split()
    if not tokens:
        return None
    number = tokens[-1]
    if not _looks_like_course_number(number):
        return None
    return DirectoryCourse(subject=subject, number=number, title=title)


_COURSE_NUMBER_RE = re.compile(r"^[A-Z]{1,3}\d{3,4}[A-Z]?$")


def _looks_like_course_number(s: str) -> bool:
    return bool(_COURSE_NUMBER_RE.match(s))


_ENROLL_RE = re.compile(r"(\d+)\s+students(?:\s+\((\d+)\s+max\))?", re.IGNORECASE)
_SECTION_RE = re.compile(r"Section\s+(\S+)", re.IGNORECASE)


def _parse_section_row(tr: Tag) -> DirectorySection | None:
    details = tr.find("div", class_="course-details")
    if not isinstance(details, Tag):
        return None
    dl = details.find("dl")
    if not isinstance(dl, Tag):
        return None

    fields = _parse_dl(dl)
    h1 = dl.find("h1")
    title_variant = h1.get_text(strip=True) if isinstance(h1, Tag) else None

    section_a = tr.find("a")
    section_label = ""
    if isinstance(section_a, Tag):
        m = _SECTION_RE.search(section_a.get_text(strip=True))
        if m:
            section_label = m.group(1)

    en_current, en_max = _parse_enrollment(fields.get("Enrollment:"))

    return DirectorySection(
        section=section_label,
        call_number=fields.get("Call Number:", ""),
        title_variant=title_variant,
        instructor=fields.get("Instructor:"),
        credits=_safe_float(fields.get("Points:", "0")),
        enrollment_current=en_current,
        enrollment_max=en_max,
    )


def _parse_dl(dl: Tag) -> dict[str, str]:
    out: dict[str, str] = {}
    dts = dl.find_all("dt")
    dds = dl.find_all("dd")
    for dt, dd in zip(dts, dds):
        key = dt.get_text(strip=True)
        out[key] = dd.get_text(strip=True)
    return out


def _parse_enrollment(s: str | None) -> tuple[int, int | None]:
    if not s:
        return (0, None)
    m = _ENROLL_RE.search(s)
    if not m:
        return (0, None)
    return (int(m.group(1)), int(m.group(2)) if m.group(2) else None)


def _safe_float(s: str | None) -> float:
    if not s:
        return 0.0
    try:
        return float(s.strip())
    except ValueError:
        return 0.0
