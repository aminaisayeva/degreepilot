"""Resolve `_dynamic` requirement markers against the merged catalog and
validate that every requirement-referenced course exists."""

from __future__ import annotations

import copy


def expand_dynamic_requirements(
    programs: dict[str, list[dict]], catalog: list[dict]
) -> dict[str, list[dict]]:
    by_category: dict[str, list[str]] = {}
    codes = {c["code"] for c in catalog}
    for c in catalog:
        for cat in c.get("categories") or []:
            by_category.setdefault(cat, []).append(c["code"])
    for lst in by_category.values():
        lst.sort()

    out = copy.deepcopy(programs)
    for reqs in out.values():
        for req in reqs:
            marker = req.pop("_dynamic", None)
            if not marker:
                continue
            hand = [c for c in req.get("courses") or [] if c in codes]
            dynamic = [c for c in by_category.get(marker, []) if c not in hand]
            req["courses"] = hand + dynamic
    return out


def add_prefix_variants(
    programs: dict[str, list[dict]], catalog: list[dict]
) -> dict[str, list[dict]]:
    """Columbia's directory sometimes lists the same course under different
    letter prefixes across terms (COMS W6706 vs COMS E6706). When a
    requirement references one spelling and the catalog contains a
    same-title prefix variant, add the variant as an accepted alternative so
    student records using either code count."""
    import re

    num_re = re.compile(r"^([A-Z]{2,4})\s+[A-Z]{0,2}(\d{4})$")
    by_dept_num: dict[tuple[str, str], list[dict]] = {}
    for c in catalog:
        m = num_re.match(c["code"])
        if m:
            by_dept_num.setdefault((m.group(1), m.group(2)), []).append(c)

    def norm_title(t: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (t or "").lower())

    out = copy.deepcopy(programs)
    for reqs in out.values():
        for req in reqs:
            extras: list[str] = []
            for code in req.get("courses") or []:
                m = num_re.match(code)
                if not m:
                    continue
                base = next((c for c in by_dept_num.get((m.group(1), m.group(2)), [])
                             if c["code"] == code), None)
                for cand in by_dept_num.get((m.group(1), m.group(2)), []):
                    if cand["code"] == code or cand["code"] in extras:
                        continue
                    if cand["code"] in (req.get("courses") or []):
                        continue
                    if base is None or norm_title(cand.get("title", "")) == norm_title(base.get("title", "")):
                        extras.append(cand["code"])
            req["courses"] = list(req.get("courses") or []) + extras
    return out


def validate_catalog(courses: list[dict], programs: dict[str, list[dict]]) -> None:
    codes = {c["code"] for c in courses}
    missing: list[str] = []
    for program, reqs in programs.items():
        for req in reqs:
            for code in req.get("courses") or []:
                if code not in codes:
                    missing.append(f"{code} (program={program}, requirement={req['name']!r})")
    if missing:
        raise ValueError(
            "Requirements reference courses missing from the catalog:\n  "
            + "\n  ".join(missing)
        )
