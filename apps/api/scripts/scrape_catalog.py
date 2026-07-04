"""One-shot Columbia catalog scrape → JSON snapshots in app/seed/data/.

Usage (from apps/api, venv active):
    python -m scripts.scrape_catalog                 # everything
    python -m scripts.scrape_catalog --only bulletin
    python -m scripts.scrape_catalog --only directory

Never imported by the app at runtime; the loader reads the JSON output.
Failures are recorded per page in the snapshot (`error` field) and the
script exits 1 if *every* page failed, 0 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.services.sync.bulletin import BulletinCourse, parse_bulletin_courses, parse_courselists
from app.services.sync.columbia_directory import DirectoryCourse, fetch_subject_term
from app.services.sync.cs_pathways import parse_pathway_page

DATA_DIR = Path(__file__).resolve().parents[1] / "app" / "seed" / "data"
_UA = "DegreePilot/0.1 (academic project; contact: aminaisayeva@degreepilot.dev)"

BULLETIN_PAGES: dict[str, str] = {
    "cs": "https://bulletin.columbia.edu/columbia-college/departments-instruction/computer-science/",
    "econ": "https://bulletin.columbia.edu/columbia-college/departments-instruction/economics/",
    "math": "https://bulletin.columbia.edu/columbia-college/departments-instruction/mathematics/",
    "stat": "https://bulletin.columbia.edu/columbia-college/departments-instruction/statistics/",
    # Core hub has no course data — the subpages do (verified 2026-07-04).
    "core_lithum": "https://bulletin.columbia.edu/columbia-college/core-curriculum/literature-humanities/",
    "core_cc": "https://bulletin.columbia.edu/columbia-college/core-curriculum/contemporary-civilization/",
    "core_arthum": "https://bulletin.columbia.edu/columbia-college/core-curriculum/art-humanities/",
    "core_musichum": "https://bulletin.columbia.edu/columbia-college/core-curriculum/music-humanities/",
    "core_uwriting": "https://bulletin.columbia.edu/columbia-college/core-curriculum/university-writing/",
    "core_frontiers": "https://bulletin.columbia.edu/columbia-college/core-curriculum/frontiers-science/",
    "core_science": "https://bulletin.columbia.edu/columbia-college/core-curriculum/science-requirement/",
    "core_globalcore": "https://bulletin.columbia.edu/columbia-college/core-curriculum/global-core-requirement/",
    # SEAS CS dept page carries 4000/6000-level courseblocks; the MS
    # requirement lists are not on the bulletin (they live on cs.columbia.edu)
    # so MS requirement lists stay curated and get verified via the dashboard.
    "ms_cs": "https://bulletin.columbia.edu/columbia-engineering/academic-departments-programs/computer-science/",
}

DIRECTORY_TERMS = ("Fall2025", "Spring2026", "Fall2026")
DIRECTORY_SUBJECTS = ("COMS", "CSEE", "ECON", "MATH", "STAT", "IEOR")

# MS pathway pages on the CS department site (not the bulletin).
PATHWAY_PAGES: dict[str, str] = {
    "ml": "https://www.cs.columbia.edu/education/ms/machineLearning/",
    "nlp": "https://www.cs.columbia.edu/education/ms/nlp/",
    "security": "https://www.cs.columbia.edu/education/ms/newComputerSecurity/",
    "software": "https://www.cs.columbia.edu/education/ms/softwareSystems/",
    "networks": "https://www.cs.columbia.edu/education/ms/networkSystems/",
    "compbio": "https://www.cs.columbia.edu/education/ms/computationalBiology/",
    "foundations": "https://www.cs.columbia.edu/education/ms/foundationsOfCS/",
    "vgir": "https://www.cs.columbia.edu/education/ms/visionAndGraphics/",
    "personalized": "https://www.cs.columbia.edu/education/ms/MSpersonalized/",
    "thesis": "https://www.cs.columbia.edu/education/ms/MSThesis/",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bulletin_snapshot(*, source_url: str, courses: list[BulletinCourse],
                      courselists: list[dict], scraped_at: str,
                      error: str | None = None) -> dict:
    return {
        "source_url": source_url,
        "scraped_at": scraped_at,
        "courses": [asdict(c) for c in courses],
        "courselists": courselists,
        "error": error,
    }


def directory_snapshot(*, term: str, subjects: dict, scraped_at: str) -> dict:
    subj_out = {}
    for name, payload in subjects.items():
        courses = payload.get("courses") or []
        subj_out[name] = {
            "courses": [
                {"code": c.code, "title": c.title, "credits": c.credits}
                for c in courses
            ],
            "error": payload.get("error"),
        }
    return {"term": term, "scraped_at": scraped_at, "subjects": subj_out}


def write_snapshot(snapshot: dict, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n")
    return path


def scrape_bulletin(client: httpx.Client) -> int:
    ok = 0
    for slug, url in BULLETIN_PAGES.items():
        scraped_at = _now()
        try:
            r = client.get(url)
            r.raise_for_status()
            snap = bulletin_snapshot(
                source_url=url,
                courses=parse_bulletin_courses(r.text),
                courselists=parse_courselists(r.text),
                scraped_at=scraped_at,
            )
            ok += 1
        except Exception as e:  # record, keep going
            snap = bulletin_snapshot(source_url=url, courses=[], courselists=[],
                                     scraped_at=scraped_at, error=str(e)[:240])
        path = write_snapshot(snap, DATA_DIR / f"bulletin_{slug}.json")
        if snap["error"]:
            print(f"  bulletin:{slug:12s} ERR {snap['error'][:80]} -> {path.name}")
        else:
            print(f"  bulletin:{slug:12s} {len(snap['courses'])} courses, "
                  f"{len(snap['courselists'])} lists -> {path.name}")
    return ok


def scrape_directory(client: httpx.Client) -> int:
    ok = 0
    for term in DIRECTORY_TERMS:
        subjects: dict = {}
        for subj in DIRECTORY_SUBJECTS:
            try:
                courses: list[DirectoryCourse] = fetch_subject_term(subj, term, client=client)
                subjects[subj] = {"courses": courses, "error": None}
                ok += 1
            except Exception as e:
                subjects[subj] = {"courses": [], "error": str(e)[:240]}
        snap = directory_snapshot(term=term, subjects=subjects, scraped_at=_now())
        path = write_snapshot(snap, DATA_DIR / f"directory_{term}.json")
        total = sum(len(s["courses"]) for s in snap["subjects"].values())
        errs = [f"{k}:{v['error'][:40]}" for k, v in snap["subjects"].items() if v["error"]]
        suffix = f" (errors: {', '.join(errs)})" if errs else ""
        print(f"  directory:{term} {total} courses -> {path.name}{suffix}")
    return ok


def scrape_pathways(client: httpx.Client) -> int:
    ok = 0
    pathways: dict = {}
    for slug, url in PATHWAY_PAGES.items():
        try:
            r = client.get(url)
            r.raise_for_status()
            page = parse_pathway_page(r.text)
            pathways[slug] = {"source_url": url, **page, "error": None}
            ok += 1
            n_entries = sum(len(s["entries"]) for s in page["sections"])
            print(f"  pathway:{slug:14s} {len(page['sections'])} sections, {n_entries} rows")
        except Exception as e:
            pathways[slug] = {"source_url": url, "title": "", "sections": [],
                              "error": str(e)[:240]}
            print(f"  pathway:{slug:14s} ERR {str(e)[:80]}")
    snap = {"scraped_at": _now(), "pathways": pathways}
    path = write_snapshot(snap, DATA_DIR / "ms_pathways.json")
    print(f"  -> {path.name}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["bulletin", "directory", "pathways"], default=None)
    args = ap.parse_args()
    ok = 0
    with httpx.Client(timeout=30.0, headers={"User-Agent": _UA}, follow_redirects=True) as client:
        if args.only in (None, "bulletin"):
            print("Scraping bulletin pages…")
            ok += scrape_bulletin(client)
        if args.only in (None, "directory"):
            print("Scraping directory terms…")
            ok += scrape_directory(client)
        if args.only in (None, "pathways"):
            print("Scraping MS pathway pages…")
            ok += scrape_pathways(client)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
