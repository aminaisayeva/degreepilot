"""Seed degree requirements — Columbia College.

Programs modeled (faithful to the CC bulletin structure):
  - columbia_cc_core           (Core Curriculum — required for every CC student)
  - columbia_cs_major          (Major in Computer Science)
  - columbia_econ_concentration (Concentration in Economics — Columbia's
                                 formal equivalent of a minor)

Sources:
  - https://bulletin.columbia.edu/columbia-college/requirements-degree-bachelor-arts/
  - https://bulletin.columbia.edu/columbia-college/core-curriculum/
  - https://bulletin.columbia.edu/columbia-college/departments-instruction/computer-science/
  - https://bulletin.columbia.edu/columbia-college/departments-instruction/economics/

Sample data — clearly marked in the UI. Not an official audit.
"""

from __future__ import annotations

from app.models.requirement import RequirementType


# --- Columbia College Core Curriculum ---
# Faithful to the BA degree bulletin: Lit Hum, CC, Art Hum, Music Hum,
# Frontiers, University Writing, Foreign Language, Global Core, Science
# Requirement (beyond Frontiers), Physical Education.
CC_CORE_REQS: list[dict] = [
    {
        "name": "University Writing",
        "type": RequirementType.ALL_OF,
        "courses": ["ENGL CC1010"],
        "credits_required": 3,
        "display_order": 10,
    },
    {
        "name": "Science A: Frontiers of Science",
        "type": RequirementType.ALL_OF,
        "courses": ["SCNC CC1000"],
        "credits_required": 3,
        "display_order": 20,
        "notes": "Science A of the three-course science requirement. Required in the first year.",
    },
    {
        "name": "Literature Humanities (year-long)",
        "type": RequirementType.ALL_OF,
        "courses": ["HUMA CC1001", "HUMA CC1002"],
        "credits_required": 8,
        "display_order": 30,
        "notes": "Two-semester sequence; both HUMA CC1001 and HUMA CC1002 required.",
    },
    {
        "name": "Contemporary Civilization (year-long)",
        "type": RequirementType.ALL_OF,
        "courses": ["COCI CC1101", "COCI CC1102"],
        "credits_required": 8,
        "display_order": 40,
        "notes": "Two-semester sequence; both COCI CC1101 and COCI CC1102 required.",
    },
    {
        "name": "Art Humanities",
        "type": RequirementType.ALL_OF,
        "courses": ["HUMA UN1121"],
        "credits_required": 3,
        "display_order": 50,
    },
    {
        "name": "Music Humanities",
        "type": RequirementType.ALL_OF,
        "courses": ["HUMA UN1123"],
        "credits_required": 3,
        "display_order": 60,
    },
    {
        "name": "Foreign Language (Intermediate II)",
        "type": RequirementType.ALL_OF,
        "courses": ["LANG CC2102"],
        "credits_required": 4,
        "display_order": 70,
        "notes": "Completion at the Intermediate II level in a single approved language, or exemption.",
    },
    # The science requirement is three courses across Science A/B/C.
    # A = Frontiers (above); B and C expand at seed time from the approved
    # lists scraped from the bulletin's science-requirement page. The lists
    # overlap by design; B and C must be satisfied by two DISTINCT courses.
    {
        "name": "Science B (pick 1)",
        "type": RequirementType.N_OF,
        "courses": ["BIOL UN2005", "CHEM UN1403", "PHYS UN1401", "ASTR UN1403"],
        "_dynamic": "core_science_b",
        "count_required": 1,
        "credits_required": 3,
        "display_order": 80,
        "notes": "One course from the Science B approved list (seven science departments).",
    },
    {
        "name": "Science C (pick 1 more)",
        "type": RequirementType.N_OF,
        "courses": ["BIOL UN2005", "CHEM UN1403", "PHYS UN1401", "ASTR UN1403"],
        "_dynamic": "core_science_c",
        "count_required": 1,
        "credits_required": 3,
        "display_order": 85,
        "notes": "One additional course from the broader Science C approved list — "
                 "must be a second, distinct course from the one used for Science B.",
    },
    {
        "name": "Global Core (pick 2)",
        "type": RequirementType.N_OF,
        # Expanded at seed time to the full approved list scraped from the
        # bulletin's global-core-requirement page (category: core_global).
        "courses": ["AHUM UN1399", "AHUM UN1400", "HIST UN2702"],
        "_dynamic": "core_global",
        "count_required": 2,
        "credits_required": 6,
        "display_order": 90,
        "notes": "Two courses from the approved Global Core list.",
    },
    {
        "name": "Physical Education",
        "type": RequirementType.N_OF,
        "courses": ["PHED UN1001", "PHED UN1002"],
        "count_required": 2,
        "credits_required": 2,
        "display_order": 100,
        "notes": "Two PE courses; pass/withdraw only. Swim test also required separately.",
    },
]

# --- CS Major (Columbia College) ---
# Faithful to the bulletin: math (calculus + LA + prob/stat),
# CS core (intro + DS + adv programming + discrete + theory + systems),
# 3 area foundation courses, 3 CS electives (3000+).
CS_MAJOR_REQS: list[dict] = [
    {
        "name": "Math: Calculus",
        "type": RequirementType.ONE_OF,
        "courses": ["MATH UN1201", "MATH UN1205", "APMA E2000"],
        "credits_required": 3,
        "display_order": 10,
        "notes": "Multivariable calculus. One of MATH UN1201, MATH UN1205, or APMA E2000.",
    },
    {
        "name": "Math: Linear Algebra",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W3251", "MATH UN2010", "MATH UN2015", "APMA E3101"],
        "credits_required": 3,
        "display_order": 20,
        "notes": "One linear algebra course. MATH UN2015 satisfies both LA and prob/stat.",
    },
    {
        "name": "Math: Probability / Statistics",
        "type": RequirementType.ONE_OF,
        "courses": ["STAT UN1201", "MATH UN2015", "IEOR E3658", "STAT GU4001"],
        "credits_required": 3,
        "display_order": 30,
        "notes": "One probability or statistics course.",
    },
    {
        "name": "Introduction to Computer Science",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W1004", "COMS W1007"],
        "credits_required": 3,
        "display_order": 40,
        "notes": "COMS W1004 or W1007. Credit only for one.",
    },
    {
        "name": "Data Structures",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W3134", "COMS W3136", "COMS W3137"],
        "credits_required": 3,
        "display_order": 50,
        "notes": "COMS W3134, W3136, or W3137. Honors version covers more.",
    },
    {
        "name": "Advanced Programming",
        "type": RequirementType.ALL_OF,
        "courses": ["COMS W3157"],
        "credits_required": 4,
        "display_order": 60,
    },
    {
        "name": "Discrete Mathematics",
        "type": RequirementType.ALL_OF,
        "courses": ["COMS W3203"],
        "credits_required": 3,
        "display_order": 70,
    },
    {
        "name": "Computer Science Theory",
        "type": RequirementType.ALL_OF,
        "courses": ["COMS W3261"],
        "credits_required": 3,
        "display_order": 80,
    },
    {
        "name": "Computer Systems Fundamentals",
        "type": RequirementType.ALL_OF,
        "courses": ["CSEE W3827"],
        "credits_required": 3,
        "display_order": 90,
    },
    {
        "name": "Area Foundation Courses (pick 3)",
        "type": RequirementType.N_OF,
        # Full list from the CC bulletin "Area Foundation Courses (9 to 12
        # points)" table (scraped 2026-07-04).
        "courses": [
            "COMS W4111",
            "COMS W4113",
            "COMS W4115",
            "COMS W4118",
            "COMS W4119",
            "COMS W4152",
            "COMS W4156",
            "COMS W4160",
            "COMS W4167",
            "COMS W4170",
            "COMS W4181",
            "CSOR E4231",
            "COMS W4236",
            "COMS W4701",
            "COMS W4705",
            "COMS W4731",
            "COMS W4733",
            "CBMF W4761",
            "COMS W4771",
            "CSEE W4824",
            "CSEE W4868",
        ],
        "count_required": 3,
        "credits_required": 9,
        "display_order": 100,
        "notes": "Three Area Foundation courses (9-12 points). Pick a track for depth.",
    },
    {
        "name": "Computer Science Electives (3000+)",
        "type": RequirementType.N_OF,
        # Hand-picked preferred head; expanded at seed time to every COMS/CSEE
        # 3000+ course worth ≥3 points in the catalog.
        "courses": [
            "COMS W4111",
            "COMS W4115",
            "COMS W4118",
            "COMS W4119",
            "COMS W4156",
            "COMS W4170",
            "COMS W4181",
            "COMS W4231",
            "COMS W4236",
            "COMS W4701",
            "COMS W4705",
            "COMS W4731",
            "COMS W4771",
            "COMS W4774",
        ],
        "_dynamic": "cs_elective_eligible",
        "count_required": 3,
        "credits_required": 9,
        "display_order": 110,
        "notes": "Three additional CS/CSEE/CBMF courses at the 3000+ level (≥3 points each).",
    },
]

# --- Econ Concentration (Columbia College) ---
# Bulletin: "Concentration in Economics" — 34 points minimum.
# Core (16) + Math (6) + Stat (3) + 3 electives at 3000-level (9).
ECON_CONCENTRATION_REQS: list[dict] = [
    {
        "name": "Principles of Economics",
        "type": RequirementType.ALL_OF,
        "courses": ["ECON UN1105"],
        "credits_required": 4,
        "display_order": 10,
    },
    {
        "name": "Intermediate Microeconomics",
        "type": RequirementType.ALL_OF,
        "courses": ["ECON UN3211"],
        "credits_required": 4,
        "display_order": 20,
    },
    {
        "name": "Intermediate Macroeconomics",
        "type": RequirementType.ALL_OF,
        "courses": ["ECON UN3213"],
        "credits_required": 4,
        "display_order": 30,
    },
    {
        "name": "Introduction to Econometrics",
        "type": RequirementType.ALL_OF,
        "courses": ["ECON UN3412"],
        "credits_required": 4,
        "display_order": 40,
    },
    {
        "name": "Calculus I",
        "type": RequirementType.ALL_OF,
        "courses": ["MATH UN1101"],
        "credits_required": 3,
        "display_order": 50,
        "notes": "Anchor of the required calculus sequence.",
    },
    {
        "name": "Multivariable Calculus",
        "type": RequirementType.ONE_OF,
        "courses": ["MATH UN1201", "MATH UN1205"],
        "credits_required": 3,
        "display_order": 60,
        "notes": "Second course in the calculus sequence.",
    },
    {
        "name": "Statistics",
        "type": RequirementType.ALL_OF,
        "courses": ["STAT UN1201"],
        "credits_required": 3,
        "display_order": 70,
        "notes": "STAT UN1201 (or a higher-level statistics course).",
    },
    {
        "name": "Economics Electives (3000+, pick 3)",
        "type": RequirementType.N_OF,
        # Hand-picked preferred head; expanded at seed time to every ECON
        # 3000+ course in the catalog.
        "courses": [
            "ECON UN3025",
            "ECON GU4280",
            "ECON GU4370",
            "ECON GU4918",
        ],
        "_dynamic": "econ_elective_3000",
        "count_required": 3,
        "credits_required": 9,
        "display_order": 80,
        "notes": "Three electives at the 3000-level or above; max one at 2000-level.",
    },
]


# --- MS in Computer Science (SEAS graduate) ---
# Curated model of the 30-point MS: three breadth areas, four track-depth
# graduate courses, and three graduate electives (10 courses ≈ 30 points).
# Students admitted to the MS are assumed to hold a CS bachelor's, so
# undergraduate prerequisites (sub-4000-level) are treated as satisfied.
MS_CS_REQS: list[dict] = [
    {
        "name": "Breadth: Systems",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W4118", "COMS W4111", "COMS W4115"],
        "credits_required": 3,
        "display_order": 10,
        "notes": "One graduate-eligible systems course (OS, databases, or PLT).",
    },
    {
        "name": "Breadth: Theory",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W4231", "COMS W4236"],
        "credits_required": 3,
        "display_order": 20,
        "notes": "One algorithms/complexity course.",
    },
    {
        "name": "Breadth: AI & Applications",
        "type": RequirementType.ONE_OF,
        "courses": ["COMS W4701", "COMS W4771", "COMS W4705"],
        "credits_required": 3,
        "display_order": 30,
        "notes": "One AI, machine learning, or NLP course.",
    },
    {
        "name": "Track Depth (pick 4)",
        "type": RequirementType.N_OF,
        "courses": [
            "COMS E6111",
            "COMS E6118",
            "COMS E6181",
            "COMS E6156",
            "COMS E6232",
            "COMS E6261",
            "COMS E6253",
            "COMS E6772",
            "COMS E6732",
            "COMS E6893",
        ],
        "count_required": 4,
        "credits_required": 12,
        "display_order": 40,
        "notes": "Four 6000-level courses forming your track depth (ML, Systems, or Theory).",
    },
    {
        "name": "Graduate Electives (pick 3)",
        "type": RequirementType.N_OF,
        # Hand-picked preferred head; expanded at seed time to every COMS/CSEE
        # 4000+ course in the catalog.
        "courses": [
            "COMS E6998",
            "COMS W4156",
            "COMS W4170",
            "COMS W4181",
            "COMS W4119",
            "COMS W4731",
            "COMS W4774",
        ],
        "_dynamic": "ms_grad_eligible",
        "count_required": 3,
        "credits_required": 9,
        "display_order": 50,
        "notes": "Three additional graduate-eligible CS courses (4000-level or above).",
    },
]


PROGRAMS: dict[str, list[dict]] = {
    "columbia_cc_core": CC_CORE_REQS,
    "columbia_cs_major": CS_MAJOR_REQS,
    "columbia_econ_concentration": ECON_CONCENTRATION_REQS,
    "columbia_ms_cs": MS_CS_REQS,
}


# Friendly labels for the frontend
PROGRAM_LABELS: dict[str, str] = {
    "columbia_cc_core": "Core Curriculum",
    "columbia_cs_major": "CS Major",
    "columbia_econ_concentration": "Econ Concentration",
    "columbia_ms_cs": "MS in CS — General",
}


# MS pathway programs (cs.columbia.edu): each pathway is its own program
# sharing the breadth cards, with track-specific requirements generated from
# the committed ms_pathways.json snapshot. Imported last to avoid cycles.
from app.seed.requirements_ms_tracks import TRACK_LABELS, build_track_programs  # noqa: E402

PROGRAMS.update(build_track_programs(MS_CS_REQS))
PROGRAM_LABELS.update(TRACK_LABELS)
