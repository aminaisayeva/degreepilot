"""Seed catalog — Columbia College Core Curriculum + Computer Science + Economics.

Curated from the Columbia Bulletin:
  - https://bulletin.columbia.edu/columbia-college/requirements-degree-bachelor-arts/
  - https://bulletin.columbia.edu/columbia-college/core-curriculum/
  - https://bulletin.columbia.edu/columbia-college/departments-instruction/computer-science/
  - https://bulletin.columbia.edu/columbia-college/departments-instruction/economics/

Course codes follow Columbia's canonical format (e.g. "COMS W1004", "MATH UN1101",
"HUMA CC1001"). Prerequisite chains are modeled in CNF (list of OR-groups). Term
offerings, credits, workload levels, and career tags are curated approximations —
clearly marked as sample data in the UI. Not an official catalog.
"""

from app.seed.overlays import ALL_CURATED

CS_AND_ECON_COURSES: list[dict] = ALL_CURATED
