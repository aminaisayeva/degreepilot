"""Merge scraped snapshots (app/seed/data/) with the curated overlay.

Precedence:  curated > bulletin > directory  for title/description/credits;
curated-only for prereqs/tags/workload; categories = curated ∪ derived;
offered_terms = curated ∪ directory seasons.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.seed.overlays import CURATED

DATA_DIR = Path(__file__).resolve().parent / "data"
_NUM_RE = re.compile(r"(\d{3,4})")


def _number_int(number: str) -> int:
    m = _NUM_RE.search(number)
    return int(m.group(1)) if m else 0


def _season(term: str) -> str:
    for s in ("Fall", "Spring", "Summer"):
        if term.startswith(s):
            return s
    return term


def derive_categories(code: str, department: str, number_int: int, credits: float) -> list[str]:
    out: list[str] = []
    if department in {"COMS", "CSEE"} and number_int >= 3000 and credits >= 3:
        out.append("cs_elective_eligible")
    if department == "ECON" and number_int >= 3000:
        out.append("econ_elective_3000")
    if department in {"COMS", "CSEE"} and number_int >= 4000:
        out.append("ms_grad_eligible")
    return out


@dataclass
class Snapshots:
    bulletin: dict[str, dict] = field(default_factory=dict)
    directory: dict[str, dict] = field(default_factory=dict)
    courselists: dict[str, list[dict]] = field(default_factory=dict)


def load_snapshots(data_dir: Path | None = None) -> Snapshots:
    data_dir = data_dir or DATA_DIR
    snaps = Snapshots()
    if not data_dir.exists():
        return snaps
    for path in sorted(data_dir.glob("bulletin_*.json")):
        payload = json.loads(path.read_text())
        slug = path.stem.removeprefix("bulletin_")
        snaps.courselists[slug] = payload.get("courselists") or []
        for c in payload.get("courses") or []:
            code = c["code"]
            if code not in snaps.bulletin:
                snaps.bulletin[code] = {
                    **c,
                    "source_url": payload.get("source_url"),
                    "scraped_at": payload.get("scraped_at"),
                }
    for path in sorted(data_dir.glob("directory_*.json")):
        payload = json.loads(path.read_text())
        season = _season(payload.get("term", ""))
        for subj in (payload.get("subjects") or {}).values():
            for c in subj.get("courses") or []:
                entry = snaps.directory.setdefault(
                    c["code"],
                    {"title": c["title"], "credits": c["credits"], "seasons": []},
                )
                if season and season not in entry["seasons"]:
                    entry["seasons"].append(season)
                if c["credits"] and not entry["credits"]:
                    entry["credits"] = c["credits"]
    return snaps


def build_catalog(data_dir: Path | None = None) -> tuple[list[dict], dict[str, dict]]:
    from app.services.sync.syncer import _pretty_title

    snaps = load_snapshots(data_dir)
    codes = sorted(set(CURATED) | set(snaps.bulletin) | set(snaps.directory))
    courses: list[dict] = []
    provenance: dict[str, dict] = {}

    for code in codes:
        curated = CURATED.get(code)
        bull = snaps.bulletin.get(code)
        dirc = snaps.directory.get(code)

        department = (curated or {}).get("department") or code.split()[0]
        number = code.split()[-1]
        credits = (
            (curated or {}).get("credits")
            or (bull or {}).get("points_max")
            or (dirc or {}).get("credits")
            or 3.0
        )
        # Directory-only zero-credit rows are recitations — skip inserts.
        if curated is None and bull is None and dirc is not None and (dirc["credits"] or 0) <= 0:
            continue

        title = (
            (curated or {}).get("title")
            or (bull or {}).get("title")
            or _pretty_title((dirc or {}).get("title", code))
        )
        description = (curated or {}).get("description") or (bull or {}).get("description") or ""
        terms = list((curated or {}).get("offered_terms") or [])
        for s in (dirc or {}).get("seasons", []):
            if s not in terms:
                terms.append(s)

        cats = list((curated or {}).get("categories") or [])
        for dc in derive_categories(code, department, _number_int(number), credits):
            if dc not in cats:
                cats.append(dc)

        courses.append({
            "code": code,
            "title": title,
            "department": department,
            "credits": float(credits),
            "description": description,
            "workload_level": (curated or {}).get("workload_level", 3),
            "offered_terms": terms,
            "prerequisites": list((curated or {}).get("prerequisites") or []),
            "categories": cats,
            "career_tags": list((curated or {}).get("career_tags") or []),
        })
        origin = "curated" if curated else ("bulletin" if bull else "directory")
        provenance[code] = {
            "origin": origin,
            "source_url": (bull or {}).get("source_url"),
            "scraped_at": (bull or {}).get("scraped_at"),
            "bulletin_prereq_text": (bull or {}).get("prereq_text", ""),
        }
    return courses, provenance
