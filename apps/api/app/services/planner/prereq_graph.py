"""Prerequisite graph utilities.

Prereqs are stored as CNF: list of OR-groups. A course is unlockable when *every*
OR-group has at least one member in the student's completed set.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field

from app.models.course import Course

_LEVEL_RE = re.compile(r"(\d{4})")


def assumed_completed(programs: list[str], catalog: dict[str, Course]) -> set[str]:
    """Course codes treated as satisfied without being taken here.

    Graduate students are admitted with a CS bachelor's, so undergraduate
    (sub-4000-level) prerequisites are considered met.
    """
    if not any(p.startswith("columbia_ms") for p in programs):
        return set()
    out: set[str] = set()
    for code in catalog:
        m = _LEVEL_RE.search(code)
        if m and int(m.group(1)) < 4000:
            out.add(code)
    return out


@dataclass
class PrereqGraph:
    nodes: dict[str, Course]
    edges_out: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    edges_in: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))

    def prereqs_for(self, code: str) -> list[list[str]]:
        c = self.nodes.get(code)
        return c.prerequisites if c else []

    def unlocks(self, code: str) -> list[str]:
        """Courses that have `code` listed as a prereq option."""
        return sorted(self.edges_out.get(code, set()))

    def topo_levels(self) -> dict[str, int]:
        """Best-effort topological depth for each node (max over OR-groups)."""
        depth: dict[str, int] = {}

        def compute(code: str, stack: set[str]) -> int:
            if code in depth:
                return depth[code]
            if code in stack:
                # cycle defense — flatten to 0
                return 0
            stack.add(code)
            course = self.nodes.get(code)
            if not course or not course.prerequisites:
                depth[code] = 0
                stack.discard(code)
                return 0
            d = 0
            for group in course.prerequisites:
                if not group:
                    continue
                # OR-group: depth is the min of options (easiest path)
                group_d = min((compute(p, stack) for p in group if p in self.nodes), default=0)
                d = max(d, group_d + 1)
            depth[code] = d
            stack.discard(code)
            return d

        for code in self.nodes:
            compute(code, set())
        return depth


def build_prereq_graph(courses: list[Course]) -> PrereqGraph:
    nodes = {c.code: c for c in courses}
    g = PrereqGraph(nodes=nodes)
    for c in courses:
        for group in c.prerequisites or []:
            for pre in group:
                if pre in nodes:
                    g.edges_out[pre].add(c.code)
                    g.edges_in[c.code].add(pre)
    return g


def prereqs_satisfied(course: Course, completed: set[str]) -> bool:
    """True iff every OR-group in `course.prerequisites` has a hit in `completed`."""
    for group in course.prerequisites or []:
        if not group:
            continue
        if not any(p in completed for p in group):
            return False
    return True


def missing_prereqs(course: Course, completed: set[str]) -> list[list[str]]:
    """Return OR-groups that are not yet satisfied."""
    out: list[list[str]] = []
    for group in course.prerequisites or []:
        if not group:
            continue
        if not any(p in completed for p in group):
            out.append(list(group))
    return out
