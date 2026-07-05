"""Parse cs.columbia.edu FAQ pages (Bootstrap accordions).

Structure: `<h4 class="panel-title">` carries the question; the sibling
`.panel-collapse .panel-body` carries the answer.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag


def _clean(s: str) -> str:
    s = s.replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def parse_faq_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out: list[dict] = []
    for title in soup.find_all("h4", class_="panel-title"):
        question = _clean(title.get_text(" ", strip=True))
        if not question:
            continue
        body: Tag | None = None
        panel = title.find_parent(class_="panel") or title.parent
        if isinstance(panel, Tag):
            body = panel.find_next(class_="panel-body")
        if not isinstance(body, Tag):
            continue
        answer = _clean(body.get_text(" ", strip=True))
        if answer:
            out.append({"question": question, "answer": answer})
    return out
