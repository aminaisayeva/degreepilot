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
    # Barnard sections (BC-numbered) never auto-qualify for CC/SEAS electives;
    # curation must opt them in explicitly.
    if code.split()[-1].upper().startswith("BC"):
        return []
    # Administrative COMS codes (projects, CPT, fieldwork, independent
    # study, research/thesis) are never auto-derived as academic electives.
    if department == "COMS" and number_int in {3998, 4901, 4902, 4910, 4998,
                                               6900, 6901, 6902, 6910}:
        return []
    out: list[str] = []
    if department in {"COMS", "CSEE"} and number_int >= 3000 and credits >= 3:
        out.append("cs_elective_eligible")
    # Cap at 4999: ECON GR5xxx+ are graduate-school-only registration and
    # must not auto-qualify for undergraduate electives.
    if department == "ECON" and 3000 <= number_int <= 4999:
        out.append("econ_elective_3000")
    if department in {"COMS", "CSEE"} and number_int >= 4000:
        out.append("ms_grad_eligible")
    if department == "MATH" and number_int >= 2000:
        out.append("math_elective_2000")
    if department == "PHIL":
        out.append("phil_ug")
        if number_int >= 4000:
            out.append("phil_grad")
    if department in {"ENGL", "CLEN"}:
        out.append("english_lit")
    if department == "POLS":
        out.append("polisci_ug")

    # MS breadth chart (cs.columbia.edu/education/ms/breadthRequirement,
    # verified 2026-07-05): pattern-based groups with explicit exceptions.
    n = number_int
    if department == "COMS":
        in_41xx = 4100 <= n <= 4199
        in_416x_417x = 4160 <= n <= 4179
        if (in_41xx and n != 4121 and not in_416x_417x) or 4800 <= n <= 4899 or n == 4444:
            out.append("ms_breadth_systems")
        if 4200 <= n <= 4299:
            out.append("ms_breadth_theory")
        if (4700 <= n <= 4799 and n not in (4721, 4726)) or in_416x_417x:
            out.append("ms_breadth_ai")
    elif department == "CSEE" and n in (4119, 4823, 4824, 4840, 4868):
        out.append("ms_breadth_systems")
    elif department == "EECS" and n == 4340:
        out.append("ms_breadth_systems")
    elif department == "CSOR" and n in (4231, 4223):
        out.append("ms_breadth_theory")
    elif department == "CBMF" and n == 4761:
        out.append("ms_breadth_ai")
    return out


# Bulletin courselists we adopt wholesale into requirements. Codes on these
# lists that no scraped subject page covers get synthesized into the catalog
# from the list row itself (code + title). Tuples: (snapshot slug, section
# prefix or None for all lists in the snapshot, category to apply or None).
ADOPTED_LISTS: list[tuple[str, str | None, str | None]] = [
    ("cs", "Area Foundation", None),
    # Stage-3 programs (Econ major, AI minor, Data Science major, CS
    # concentration) reference these bulletin lists directly.
    ("cs", "Minor in Artificial Intelligence", None),
    ("cs", "AI Requirement", None),
    ("cs", "Ethics Requirement", None),
    ("cs", "AI Elective", None),
    ("cs", "Major in Data Science", None),
    ("cs", "Concentration in Computer Science", None),
    ("econ", "Required Coursework", None),
    # The CC science requirement is three courses across Science A/B/C.
    # Science A is SCNC CC1000 (tagged core_science_a in the curated overlay);
    # B and C are approved lists on the science-requirement page, captured as
    # per-table sections. Lists overlap by design — a course can be B and C.
    ("core_science", "Science B", "core_science_b"),
    ("core_science", "Science C", "core_science_c"),
    ("core_science", None, "core_science"),
    ("core_globalcore", None, "core_global"),
    # More-majors expansion (2026-07-05): whole-page adoptions.
    ("sustdev", None, None),
    ("phil", None, None),
    ("math", None, None),
    ("econ", "Major in", None),
    ("stat", "Major in Mathematics-Statistics", None),
]


@dataclass
class Snapshots:
    bulletin: dict[str, dict] = field(default_factory=dict)
    directory: dict[str, dict] = field(default_factory=dict)
    courselists: dict[str, list[dict]] = field(default_factory=dict)
    list_sources: dict[str, str | None] = field(default_factory=dict)
    # code -> {"title", "source_url"} from MS pathway pages (cs.columbia.edu)
    pathway_courses: dict[str, dict] = field(default_factory=dict)
    # umbrella code -> topic title -> {"credits", "seasons", "instructors"}
    topics: dict[str, dict[str, dict]] = field(default_factory=dict)


def load_snapshots(data_dir: Path | None = None) -> Snapshots:
    data_dir = data_dir or DATA_DIR
    snaps = Snapshots()
    if not data_dir.exists():
        return snaps
    for path in sorted(data_dir.glob("bulletin_*.json")):
        payload = json.loads(path.read_text())
        slug = path.stem.removeprefix("bulletin_")
        snaps.courselists[slug] = payload.get("courselists") or []
        snaps.list_sources[slug] = payload.get("source_url")
        for c in payload.get("courses") or []:
            code = c["code"]
            if code not in snaps.bulletin:
                snaps.bulletin[code] = {
                    **c,
                    "source_url": payload.get("source_url"),
                    "scraped_at": payload.get("scraped_at"),
                }
    pathway_file = data_dir / "ms_pathways.json"
    if pathway_file.exists():
        payload = json.loads(pathway_file.read_text())
        for track in (payload.get("pathways") or {}).values():
            for section in track.get("sections") or []:
                for entry in section.get("entries") or []:
                    for code in entry.get("codes") or []:
                        snaps.pathway_courses.setdefault(code, {
                            "title": entry.get("title") or code,
                            "source_url": track.get("source_url"),
                        })
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
                # Topics umbrellas (4995/6998): every section is a distinct
                # class — collect per-topic titles across terms.
                for t in c.get("topics") or []:
                    bucket = snaps.topics.setdefault(c["code"], {})
                    info = bucket.setdefault(t["title"], {
                        "credits": t.get("credits") or c["credits"] or 3.0,
                        "seasons": [],
                        "instructors": [],
                    })
                    if season and season not in info["seasons"]:
                        info["seasons"].append(season)
                    instr = t.get("instructor")
                    if instr and instr not in info["instructors"]:
                        info["instructors"].append(instr)
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

    _apply_adopted_lists(snaps, courses, provenance)
    _apply_pathway_courses(snaps, courses, provenance)
    _apply_topics(snaps, courses, provenance)
    return courses, provenance


def _apply_topics(snaps: Snapshots, courses: list[dict], provenance: dict[str, dict]) -> None:
    """Expand topics umbrellas (COMS W4995/E6998/…) into one catalog entry per
    distinct topic title. Codes are `<umbrella>-NN` in sorted-title order —
    stable for a fixed snapshot set. The umbrella entry stays for requirement
    references and gets a pointer note."""
    from app.services.sync.syncer import _pretty_title

    by_code = {c["code"]: c for c in courses}
    for umbrella, titles in snaps.topics.items():
        parent = by_code.get(umbrella)
        if parent is not None and "individual topic sections" not in parent["description"]:
            parent["description"] = (
                f"Umbrella topics course — see the individual topic sections "
                f"({umbrella}-01 …) for the actual classes. "
                + parent["description"]
            ).strip()
        department = umbrella.split()[0]
        number = umbrella.split()[-1]
        for i, title in enumerate(sorted(titles), start=1):
            info = titles[title]
            code = f"{umbrella}-{i:02d}"
            pretty = _pretty_title(title) if title.isupper() or not any(
                ch.islower() for ch in title) else title
            instructors = ", ".join(info["instructors"])
            spec = {
                "code": code,
                "title": pretty,
                "department": department,
                "credits": float(info["credits"] or 3.0),
                "description": (
                    f"Topics section of {umbrella}"
                    + (f" — taught by {instructors}" if instructors else "")
                    + ". Each section is a distinct class."
                ),
                "workload_level": (parent or {}).get("workload_level", 3),
                "prerequisites": [],
                "offered_terms": list(info["seasons"]),
                "categories": derive_categories(code, department, _number_int(number),
                                                float(info["credits"] or 3.0)),
                "career_tags": [],
            }
            courses.append(spec)
            by_code[code] = spec
            provenance[code] = {
                "origin": "directory_topic",
                "source_url": None,
                "scraped_at": None,
                "bulletin_prereq_text": "",
            }


def _apply_pathway_courses(
    snaps: Snapshots, courses: list[dict], provenance: dict[str, dict]
) -> None:
    """Synthesize catalog entries for MS-pathway-listed courses that no other
    source covers (e.g. ELEN E4720). Title comes from the pathway table row —
    for OR-rows it may describe several alternatives; the accuracy dashboard
    is the curation point."""
    by_code = {c["code"]: c for c in courses}
    for code, info in snaps.pathway_courses.items():
        if code in by_code:
            continue
        number = code.split()[-1]
        courses.append({
            "code": code,
            "title": info["title"],
            "department": code.split()[0],
            "credits": 3.0,
            "description": "",
            "workload_level": 3,
            "offered_terms": [],
            "prerequisites": [],
            "categories": derive_categories(code, code.split()[0], _number_int(number), 3.0),
            "career_tags": [],
        })
        by_code[code] = courses[-1]
        provenance[code] = {
            "origin": "pathway_list",
            "source_url": info.get("source_url"),
            "scraped_at": None,
            "bulletin_prereq_text": "",
        }


_TITLE_MARKER_RE = re.compile(r"\s*\(\*+\)\s*$")


def _apply_adopted_lists(
    snaps: Snapshots, courses: list[dict], provenance: dict[str, dict]
) -> None:
    from app.services.sync.syncer import _pretty_title

    by_code = {c["code"]: c for c in courses}
    for slug, section_prefix, category in ADOPTED_LISTS:
        for cl in snaps.courselists.get(slug, []):
            if section_prefix and not cl.get("section", "").startswith(section_prefix):
                continue
            for code in cl.get("codes", []):
                existing = by_code.get(code)
                if existing is not None:
                    if category and category not in existing["categories"]:
                        existing["categories"].append(category)
                    continue
                raw_title = cl.get("titles", {}).get(code, code)
                raw_title = _TITLE_MARKER_RE.sub("", raw_title)
                title = raw_title
                if title and not any(ch.islower() for ch in title):
                    title = _pretty_title(title)
                spec = {
                    "code": code,
                    "title": title,
                    "department": code.split()[0],
                    "credits": 3.0,
                    "description": "",
                    "workload_level": 3,
                    "offered_terms": [],
                    "prerequisites": [],
                    "categories": [category] if category else [],
                    "career_tags": [],
                }
                courses.append(spec)
                by_code[code] = spec
                provenance[code] = {
                    "origin": "bulletin_list",
                    "source_url": snaps.list_sources.get(slug),
                    "scraped_at": None,
                    "bulletin_prereq_text": "",
                }
