"""MS CS pathway programs, generated from the committed ms_pathways.json
snapshot plus a curated rules table encoding each section's semantics (the
pages state these only in prose).

Known approximations, documented in each card's notes and verifiable on the
accuracy dashboard (/admin/accuracy):
  - Group-A/B choice logic, "≥N at 6000-level" floors, and same-course
    mutual exclusions are carried as notes text, not enforced by the engine.
  - OR-rows ("COMS W4771 or COMS W4721 or ELEN 4720") are flattened into the
    candidate list; when a page says "complete the following N courses" but
    rows contain alternatives, the card is modeled as n_of N.
  - Research-credit policy (max 12 project/research points, ≤3 of E6901,
    thesis = 9 points E6902) lives in the Total card notes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.models.requirement import RequirementType

_DATA = Path(__file__).resolve().parent / "data" / "ms_pathways.json"

RESEARCH_POLICY = (
    "MS research-credit policy (cs.columbia.edu): at most 12 project/research "
    "points count toward the 30-point degree; at most 3 of those points may be "
    "COMS E6901 Projects in Computer Science (COMS E6900 Tutorial may "
    "substitute with advisor approval); only the MS Thesis pathway may count "
    "COMS E6902 (9 points required, 9 max)."
)

TRACK_LABELS: dict[str, str] = {
    "columbia_ms_cs_ml": "MS CS — Machine Learning",
    "columbia_ms_cs_nlp": "MS CS — Natural Language Processing",
    "columbia_ms_cs_security": "MS CS — Computer Security",
    "columbia_ms_cs_software": "MS CS — Software Systems",
    "columbia_ms_cs_networks": "MS CS — Network Systems",
    "columbia_ms_cs_compbio": "MS CS — Computational Biology",
    "columbia_ms_cs_foundations": "MS CS — Foundations of CS",
    "columbia_ms_cs_vgir": "MS CS — Vision, Graphics, Interaction & Robotics",
    "columbia_ms_cs_personalized": "MS CS — Personalized (faculty invite only)",
    "columbia_ms_cs_thesis": "MS CS — Thesis (faculty invite only)",
}

# Section semantics per pathway, keyed by the section's leading number in the
# scraped page. count=N → n_of N (all single-code rows and count==len(rows) →
# all_of). Sections not listed (breadth, general electives, defense) are
# handled structurally.
_SECTION_RULES: dict[str, dict[str, dict]] = {
    "ml": {"2": {"count": 2}, "3": {"count": 2}},
    "nlp": {"2": {"count": 3}, "3": {"count": 2}},
    "security": {"2": {"count": 5}, "3": {"count": 2}},
    "software": {"2": {"count": 3}, "3": {"count": 2}, "4": {"count": 2}},
    "networks": {"2": {"count": 3}, "3": {"count": 4}},
    "compbio": {"2": {"count": 2}, "3": {"count": 2}},
    "foundations": {"2": {"count": 2}, "3": {"count": 1}, "4": {"count": 3}},
    "vgir": {"2": {"count": 2}, "3": {"count": 2}},
}

_HEADING_NUM_RE = re.compile(r"^(\d+)\.\s*(.+)$")


def _load_pathways() -> dict:
    if not _DATA.exists():
        return {}
    return json.loads(_DATA.read_text()).get("pathways", {})


def _card_name(heading: str) -> str:
    m = _HEADING_NUM_RE.match(heading)
    name = (m.group(2) if m else heading).strip()
    # Normalize SHOUTY thesis-page headings and strip credit parentheticals.
    name = re.sub(r"\s*\(\d+\s*credits?\)\s*$", "", name, flags=re.IGNORECASE)
    if name.isupper():
        name = name.title()
    return name


def _breadth_cards(base_ms_reqs: list[dict]) -> list[dict]:
    return [dict(r) for r in base_ms_reqs if r["name"].startswith("Breadth:")]


def _total_card(general_note: str) -> dict:
    notes = (general_note + " " + RESEARCH_POLICY).strip()
    return {
        "name": "Total: 30 points",
        "type": RequirementType.CREDITS,
        "courses": [],
        "credits_required": 30,
        "display_order": 90,
        "notes": notes,
    }


def _table_card(section: dict, rule: dict, display_order: int) -> dict:
    entries = section.get("entries") or []
    codes: list[str] = []
    for e in entries:
        for c in e.get("codes") or []:
            if c not in codes:
                codes.append(c)
    count = rule["count"]
    all_single = all(len(e.get("codes") or []) == 1 for e in entries)
    if count == len(entries) and all_single:
        req_type = RequirementType.ALL_OF
        count_required = 0
    else:
        req_type = RequirementType.N_OF
        count_required = count
    return {
        "name": _card_name(section["heading"]),
        "type": req_type,
        "courses": codes,
        "count_required": count_required,
        "credits_required": 3 * count,
        "display_order": display_order,
        "notes": (section.get("rule_text") or "")[:600],
    }


def build_track_programs(base_ms_reqs: list[dict]) -> dict[str, list[dict]]:
    """Build {program_slug: [requirement dicts]} for all 10 pathways."""
    pathways = _load_pathways()
    breadth = _breadth_cards(base_ms_reqs)
    out: dict[str, list[dict]] = {}

    for short, rules in _SECTION_RULES.items():
        slug = f"columbia_ms_cs_{short}"
        track = pathways.get(short) or {"sections": []}
        cards: list[dict] = [dict(r) for r in breadth]
        general_note = ""
        order = 40
        for section in track.get("sections") or []:
            m = _HEADING_NUM_RE.match(section.get("heading", ""))
            num = m.group(1) if m else ""
            if num in rules and section.get("entries"):
                cards.append(_table_card(section, rules[num], order))
                order += 5
            elif "elective" in section.get("heading", "").lower():
                general_note = (section.get("rule_text") or "")[:400]
        cards.append(_total_card(general_note))
        out[slug] = cards

    out["columbia_ms_cs_personalized"] = _personalized_cards(breadth, pathways.get("personalized"))
    out["columbia_ms_cs_thesis"] = _thesis_cards(breadth, pathways.get("thesis"))
    return out


def _personalized_cards(breadth: list[dict], track: dict | None) -> list[dict]:
    sections = (track or {}).get("sections") or []
    plan_note = ""
    for s in sections:
        if s.get("heading", "").startswith("2"):
            plan_note = (s.get("rule_text") or "")[:500]
    return [
        *[dict(r) for r in breadth],
        {
            "name": "Advisor-Approved Coursework (18 points)",
            "type": RequirementType.CATEGORY_CREDITS,
            "courses": [],
            "category": "ms_grad_eligible",
            "credits_required": 18,
            "display_order": 40,
            "notes": ("By faculty invite only. " + plan_note).strip(),
        },
        _total_card(""),
    ]


def _thesis_cards(breadth: list[dict], track: dict | None) -> list[dict]:
    sections = {s.get("heading", "")[:1]: s for s in (track or {}).get("sections") or []}
    thesis_note = (sections.get("2", {}).get("rule_text") or "")[:400]
    secondary_note = (sections.get("3", {}).get("rule_text") or "")[:400]
    defense_note = (sections.get("5", {}).get("rule_text") or "")[:400]
    return [
        *[dict(r) for r in breadth],
        {
            "name": "Thesis (COMS E6902, 9 points)",
            "type": RequirementType.ALL_OF,
            "courses": ["COMS E6902"],
            "credits_required": 9,
            "display_order": 40,
            "notes": ("By faculty invite only. " + thesis_note).strip(),
        },
        {
            "name": "Secondary: Graduate Electives (9 points)",
            "type": RequirementType.CATEGORY_CREDITS,
            "courses": [],
            "category": "ms_grad_eligible",
            "credits_required": 9,
            "display_order": 50,
            "notes": secondary_note,
        },
        {
            "name": "Thesis Defense",
            "type": RequirementType.ALL_OF,
            "courses": [],
            "credits_required": 0,
            "display_order": 60,
            "notes": defense_note or "Thesis proposal + committee defense per department policy.",
        },
        _total_card(""),
    ]
