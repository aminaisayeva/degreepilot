"""Parse Columbia Bulletin (CourseLeaf) pages.

Two things live on a bulletin department page:
  - `div.courseblock`     → per-course metadata (code, title, points, description)
  - `table.sc_courselist` → requirement course lists with `areaheader` comments

The bulletin does not publish structured prereqs — only prose in
`span.prereq`. We keep that text for the accuracy dashboard; CNF prereqs stay
hand-curated in the seed overlay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

from app.services.sync.syncer import _pretty_title

_CODE_RE = re.compile(r"^([A-Z]{2,4})\s+([A-Z]{0,3}\d{3,4}[A-Z]?)\b")
_POINTS_RE = re.compile(r"(\d+(?:\.\d+)?)(?:\s*-\s*(\d+(?:\.\d+)?))?\s*points?", re.IGNORECASE)


@dataclass
class BulletinCourse:
    code: str
    subject: str
    number: str
    title: str
    points_min: float = 0.0
    points_max: float = 0.0
    description: str = ""
    prereq_text: str = ""


def parse_bulletin_courses(html: str) -> list[BulletinCourse]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[BulletinCourse] = []
    for block in soup.find_all("div", class_="courseblock"):
        title_p = block.find("p", class_="courseblocktitle")
        if not isinstance(title_p, Tag):
            continue
        raw = _clean(title_p.get_text(" ", strip=True))
        m = _CODE_RE.match(raw)
        if not m:
            continue
        subject, number = m.group(1), m.group(2)

        pm = _POINTS_RE.search(raw)
        points_min = float(pm.group(1)) if pm else 0.0
        points_max = float(pm.group(2)) if pm and pm.group(2) else points_min

        # Title = text after the code, before the points clause.
        title = raw[m.end(): pm.start()] if pm else raw[m.end():]
        title = title.strip(" .")
        if title and not any(ch.islower() for ch in title):
            title = _pretty_title(title)

        prereq_text = ""
        prereq_span = block.find("span", class_="prereq")
        if isinstance(prereq_span, Tag):
            prereq_text = _clean(prereq_span.get_text(" ", strip=True))

        # Description: longest paragraph in the block that isn't the title or
        # a prereq-only paragraph.
        description = ""
        for p in block.find_all("p"):
            if p is title_p:
                continue
            text = _clean(p.get_text(" ", strip=True))
            if not text or text == prereq_text:
                continue
            if text.startswith("Prerequisites:") or text.startswith("Corequisites:"):
                continue
            if len(text) > len(description):
                description = text
        # Skip schedule crumbs like "Lect: 3."
        if len(description) < 25:
            description = ""

        out.append(
            BulletinCourse(
                code=f"{subject} {number}",
                subject=subject,
                number=number,
                title=title,
                points_min=points_min,
                points_max=points_max,
                description=description,
                prereq_text=prereq_text,
            )
        )
    return out


def parse_courselists(html: str) -> list[dict]:
    """Extract requirement lists:
        [{"header": ..., "section": ..., "codes": [...], "titles": {code: title}}, ...]

    Rows with an `areaheader` marker start a new group; `codecol` cells carry
    canonical codes ("MATH UN1201", NBSP normalized to space). Sequence rows
    ("A & B") are split. `section` is the nearest heading (h2-h5) preceding
    the table — many bulletin tables have no in-table header at all.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Map each courselist table to the nearest preceding heading, in document
    # order over the whole page.
    sections: dict[int, str] = {}
    last_heading = ""
    for el in soup.find_all(["h2", "h3", "h4", "h5", "table"]):
        if el.name == "table":
            if "sc_courselist" in (el.get("class") or []):
                sections[id(el)] = last_heading
        else:
            last_heading = _clean(el.get_text(" ", strip=True))

    out: list[dict] = []
    for table in soup.find_all("table", class_="sc_courselist"):
        section = sections.get(id(table), "")
        current: dict | None = None
        for tr in table.find_all("tr"):
            classes = tr.get("class") or []
            header_span = tr.find("span", class_="areaheader")
            if "areaheader" in classes or header_span is not None:
                if current and current["codes"]:
                    out.append(current)
                header = _clean(tr.get_text(" ", strip=True))
                current = {"header": header, "section": section, "codes": [], "titles": {}}
                continue
            codecol = tr.find("td", class_="codecol")
            if not isinstance(codecol, Tag):
                continue
            code = _clean(codecol.get_text(" ", strip=True))
            title_td = codecol.find_next_sibling("td")
            title = _clean(title_td.get_text(" ", strip=True)) if isinstance(title_td, Tag) else ""
            for part in re.split(r"\s*&\s*", code):
                part = part.strip()
                if _CODE_RE.match(part):
                    if current is None:
                        current = {"header": "", "section": section, "codes": [], "titles": {}}
                    if part not in current["codes"]:
                        current["codes"].append(part)
                        if title:
                            current["titles"][part] = title
        if current and current["codes"]:
            out.append(current)
    return out


def _clean(s: str) -> str:
    """Normalize NBSP and zero-width characters the bulletin sprinkles in."""
    return s.replace("\xa0", " ").replace("​", "").strip()
