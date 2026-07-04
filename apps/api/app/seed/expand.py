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
