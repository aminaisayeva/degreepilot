"""Stage-5 programs: Econ joint majors, Math family, Sustainable Development,
Philosophy (BA + MA), English — all curated from the scraped bulletin dept
pages (course lists verbatim from snapshots; exact prose in notes).

Engine approximations, verifiable on /admin/accuracy:
  - Sequence choices ("one of three calculus sequences") become n_of over the
    union with the sequences spelled out in notes.
  - "N points in department" rules use derived categories
    (math_elective_2000, phil_ug, phil_grad, english_lit).
  - English genre/geography/pre-1800 distribution rules live in notes — the
    engine counts courses; the distribution is human-verified.
  - The Philosophy MA is curated (philosophy.columbia.edu blocks automated
    access) — verify manually against the department page.
"""

from __future__ import annotations

from app.models.requirement import RequirementType

ECON_CORE = ["ECON UN1105", "ECON UN3211", "ECON UN3213", "ECON UN3412"]
ECON_SEMINARS = [
    "ECON BC3029", "ECON GU4321", "ECON BC3038", "ECON GU4505",
    "ECON BC3019", "ECON GU4400", "ECON BC3047", "ECON GU4500",
    "ECON BC3039", "ECON GU4625", "ECON BC3041", "ECON GU4235",
]


def _card(name, type_, courses, order, *, count=0, credits=0, category=None,
          notes="", dynamic=None):
    card = {
        "name": name, "type": type_, "courses": courses,
        "count_required": count, "credits_required": credits,
        "display_order": order, "notes": notes,
    }
    if category:
        card["category"] = category
    if dynamic:
        card["_dynamic"] = dynamic
    return card


def _econ_base(order_start=10):
    return [
        _card("Economics Core", RequirementType.ALL_OF, list(ECON_CORE), order_start,
              credits=16, notes="All core courses by spring of junior year, at Columbia."),
        _card("Calculus I", RequirementType.ALL_OF, ["MATH UN1101"], order_start + 10, credits=3),
        _card("Multivariable Calculus", RequirementType.ONE_OF,
              ["MATH UN1201", "MATH UN1205", "MATH UN1207", "MATH UN1208"],
              order_start + 20, credits=3),
    ]


# --- Economics joint majors -------------------------------------------------

FINANCIAL_ECON_REQS = [
    *_econ_base(),
    _card("Statistics", RequirementType.ALL_OF, ["STAT UN1201"], 40, credits=3),
    _card("Finance Core", RequirementType.ALL_OF,
          ["ECON UN3025", "ECON GU4280", "ECON UN2261"], 50, credits=9,
          notes="Financial Economics, Corporate Finance, and Accounting & Finance."),
    _card("Finance Electives (pick 3)", RequirementType.N_OF,
          ["ECON BC3014", "ECON BC3017", "ECON UN3265", "ECON UN3901", "ECON UN3952",
           "ECON GU4020", "ECON GU4213", "ECON GU4251", "ECON GU4260", "ECON GU4412",
           "ECON GU4415", "ECON GU4465", "ECON GU4500", "ECON GU4505", "ECON G4526",
           "ECON GU4615", "ECON GU4630", "ECON GU4700", "ECON GU4710", "ECON GU4840",
           "ECON GU4850", "ECON GU4860", "BIOT GU4180", "ECON BC3043", "BUSI UN3021",
           "BUSI UN3701", "BUSI UN3702", "BUSI UN3703", "BUSI UN3704", "BUSI GU4377",
           "BUSI GU4518", "COMS W1002", "HIST W2904", "IEOR E4106", "IEOR E4700",
           "MATH UN3050", "MATH GR5010", "POLS UN3630", "STAT W3201", "STAT GU4261",
           "STAT GU4207", "STAT GU4262"],
          60, count=3, credits=9,
          notes="Approved financial-economics electives list (26 econ points total per bulletin)."),
    _card("Economics Seminar (pick 1)", RequirementType.N_OF, list(ECON_SEMINARS),
          70, count=1, credits=3),
]

ECON_MATH_REQS = [
    _card("Economics Core", RequirementType.ALL_OF, list(ECON_CORE), 10, credits=16),
    _card("Mathematics Sequence (pick 4)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN2010", "MATH UN1205",
           "MATH UN1207", "MATH UN1208", "MATH UN2500", "MATH UN1202", "MATH UN2030"],
          20, count=4, credits=13,
          notes="Calculus sequence through Linear Algebra plus analysis per the bulletin table."),
    _card("Statistics (pick 2)", RequirementType.N_OF,
          ["STAT GU4001", "STAT GU4203", "STAT GU4204"], 30, count=2, credits=6),
    _card("Economics Electives (pick 2)", RequirementType.N_OF,
          ["ECON UN3025", "ECON GU4280", "ECON GU4370", "ECON GU4918"], 40,
          count=2, credits=6, dynamic="econ_elective_3000",
          notes="Two econ electives at the 3000-level or above."),
    _card("Economics Seminar (pick 1)", RequirementType.N_OF, list(ECON_SEMINARS),
          50, count=1, credits=3),
]

ECON_POLISCI_REQS = [
    _card("Economics Core", RequirementType.ALL_OF,
          ["ECON UN1105", "ECON UN3211", "ECON UN3213", "ECON GU4370"], 10, credits=16,
          notes="Political-economy core per the bulletin (includes Political Economy GU4370)."),
    _card("Calculus I", RequirementType.ALL_OF, ["MATH UN1101"], 20, credits=3),
    _card("Multivariable Calculus", RequirementType.ONE_OF,
          ["MATH UN1201", "MATH UN1205", "MATH UN1207", "MATH UN1208"], 30, credits=3),
    _card("Statistical Methods (pick 2)", RequirementType.N_OF,
          ["STAT UN1201", "ECON UN3412", "POLS GU4712"], 40, count=2, credits=6),
    _card("Political Science Courses (pick 3)", RequirementType.N_OF,
          [], 50, count=3, credits=9, dynamic="polisci_ug",
          notes="Three political science courses; consult the joint-major adviser for tracks."),
    _card("Seminar (pick 1)", RequirementType.N_OF,
          ["ECPS GU4921", "POLS UN3911", "POLS UN3921", "POLS UN3951", "POLS UN3961"],
          60, count=1, credits=3),
]

ECON_STAT_REQS = [
    _card("Economics Core", RequirementType.ALL_OF, list(ECON_CORE), 10, credits=16),
    _card("Mathematics (pick 4)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN2010", "MATH UN1205",
           "MATH UN1207", "MATH UN1208"], 20, count=4, credits=13),
    _card("Statistics (pick 3)", RequirementType.N_OF,
          ["STAT UN1201", "STAT GU4203", "STAT GU4204", "STAT GU4205"], 30,
          count=3, credits=9),
    _card("Computer Science (pick 1)", RequirementType.ONE_OF,
          ["COMS W1004", "COMS W1005", "COMS W1007", "ENGI E1006", "STAT UN2102"],
          40, credits=3),
    _card("Economics Electives (pick 2)", RequirementType.N_OF,
          ["ECON UN3025", "ECON GU4280", "ECON GU4370"], 50, count=2, credits=6,
          dynamic="econ_elective_3000"),
    _card("Economics Seminar", RequirementType.ALL_OF, ["ECON GU4918"], 60, credits=3),
]

ECON_PHILOSOPHY_REQS = [
    _card("Economics Core", RequirementType.ALL_OF, list(ECON_CORE), 10, credits=16),
    _card("Calculus I", RequirementType.ALL_OF, ["MATH UN1101"], 20, credits=3),
    _card("Multivariable Calculus", RequirementType.ONE_OF,
          ["MATH UN1201", "MATH UN1205", "MATH UN1207", "MATH UN1208"], 30, credits=3),
    _card("Statistics", RequirementType.ALL_OF, ["STAT UN1201"], 40, credits=3),
    _card("Philosophy Courses (pick 4)", RequirementType.N_OF,
          ["PHIL UN1010", "PHIL UN3411", "PHIL UN3701", "PHIL UN3551", "PHIL GU4561"],
          50, count=4, credits=12,
          notes="Intro course, Symbolic Logic, one moral/political 3000-level, one "
                "epistemology/philosophy-of-science 3000-level, Probability & Decision "
                "Theory — per the joint-major page."),
    _card("Economics-Philosophy Seminar", RequirementType.ALL_OF, ["ECPH GU4950"],
          60, credits=3),
]

# --- Mathematics family -----------------------------------------------------

MATH_MAJOR_REQS = [
    _card("Calculus & Linear Algebra Sequence (pick 5)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN1202", "MATH UN2010",
           "MATH UN1205", "MATH UN1207", "MATH UN1208"], 10, count=5, credits=15,
          notes="One of three sequences: I-II-III-IV + Linear Algebra; I-II-Accelerated "
                "Multivariable + Linear Algebra; or I-II-Honors Math A-B (13-15 points)."),
    _card("Modern Algebra & Analysis (12 points)", RequirementType.N_OF,
          ["MATH GU4041", "MATH GU4042", "MATH GU4061", "MATH GU4062"], 20,
          count=4, credits=12),
    _card("Undergraduate Seminar", RequirementType.ALL_OF, ["MATH UN3951"], 30, credits=3),
    _card("Mathematics Electives (to 40 points)", RequirementType.CATEGORY_CREDITS,
          [], 40, credits=12, category="math_elective_2000",
          notes="Additional MATH courses numbered 2000+ to reach the 40-42 point total."),
]

MATH_CONCENTRATION_REQS = [
    _card("Multivariable Calculus & Linear Algebra (pick 3)", RequirementType.N_OF,
          ["MATH UN1201", "MATH UN1202", "MATH UN2010", "MATH UN1205",
           "MATH UN1207", "MATH UN1208"], 10, count=3, credits=9,
          notes="One of three sequences per the bulletin."),
    _card("Additional Mathematics (12 points, 2000+)", RequirementType.CATEGORY_CREDITS,
          [], 20, credits=12, category="math_elective_2000",
          notes="At least 12 additional points from department courses numbered 2000+; "
                "max 3 credits from outside the department."),
]

APPLIED_MATH_REQS = [
    _card("Core Sequence (pick 5)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN1202", "MATH UN2010",
           "MATH UN1205", "MATH UN1207", "MATH UN1208", "MATH UN2500", "MATH GU4032",
           "MATH GU4061"], 10, count=5, credits=15,
          notes="Calculus/linear-algebra core per the bulletin table."),
    _card("Applied Math Seminar (pick 1)", RequirementType.ONE_OF,
          ["APMA E4901", "APMA E4903"], 20, credits=3),
    _card("Track A: Analysis & Computation (pick 3)", RequirementType.N_OF,
          ["MATH UN2500", "MATH UN2030", "MATH UN3007", "MATH UN3028", "MATH GU4032",
           "MATH GU4061", "MATH GU4062", "APMA E4100", "APMA E4101", "APMA E4150",
           "APMA E4300", "APMA E4301", "APMA E6301", "APMA E6302"], 30,
          count=3, credits=9,
          notes="Track A list; students follow Track A OR Track B — the other track "
                "card then reads as electives (engine models both, verify on dashboard)."),
    _card("Track B: Discrete & Applications (pick 3)", RequirementType.N_OF,
          ["COMS W3203", "COMS W3261", "COMS W4231", "COMS W4261", "MATH UN3050",
           "MATH GU4155", "MATH GU4156", "IEOR E3106", "APMA E4008", "APMA E4306",
           "ECON GU4415"], 40, count=3, credits=9,
          notes="Track B list; see Track A note."),
]

MATH_MINOR_REQS = [
    _card("Multivariable Calculus & Linear Algebra (pick 2)", RequirementType.N_OF,
          ["MATH UN1202", "MATH UN2010", "MATH UN2015", "MATH UN1205",
           "MATH UN1207", "MATH UN1208"], 10, count=2, credits=6),
    _card("Additional Mathematics (9 points, 2000+)", RequirementType.CATEGORY_CREDITS,
          [], 20, credits=9, category="math_elective_2000"),
]

MATH_PROB_MINOR_REQS = [
    _card("Multivariable Calculus & Linear Algebra (pick 2)", RequirementType.N_OF,
          ["MATH UN1201", "MATH UN2010", "MATH UN2015", "MATH UN1205",
           "MATH UN1207", "MATH UN1208"], 10, count=2, credits=6),
    _card("Probability Theory", RequirementType.ALL_OF, ["MATH GU4155"], 20, credits=3),
    _card("Mathematics Electives (pick 2)", RequirementType.N_OF,
          ["MATH UN2030", "MATH UN2500", "MATH UN3028", "MATH UN3050",
           "MATH GU4061", "MATH GU4062", "MATH GU4156"], 30, count=2, credits=6),
    _card("Cognate Electives (pick 1)", RequirementType.N_OF,
          ["COMS W3203", "IEOR E3106", "PHIL GU4561", "PHYS GU4023",
           "STAT GU4204", "STAT GU4207", "STAT GU4262", "STAT GU4264"], 40,
          count=1, credits=3),
]

CS_MATH_REQS = [
    _card("Computer Science Core", RequirementType.ALL_OF,
          ["COMS W1004", "COMS W3134", "COMS W3157", "COMS W3203", "COMS W3261",
           "CSEE W3827"], 10, credits=19,
          notes="20 points of CS per the joint-major page (intro alternatives allowed)."),
    _card("Mathematics Sequence (pick 5)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN1202", "MATH UN2010",
           "MATH UN1205", "MATH UN1207", "MATH UN1208"], 20, count=5, credits=15,
          notes="19-21 points of mathematics."),
    _card("Algebra Requirement", RequirementType.ALL_OF, ["MATH GU4041"], 30, credits=3),
    _card("Undergraduate Seminar", RequirementType.ALL_OF, ["MATH UN3951"], 40, credits=3),
    _card("Electives (pick 2)", RequirementType.N_OF,
          ["MATH BC2006", "MATH UN2030", "MATH UN2500", "MATH UN3007", "MATH UN3020",
           "MATH UN3025", "MATH UN3028", "MATH UN3386", "MATH GU4032", "MATH GU4042",
           "MATH GU4051", "MATH GU4053", "MATH GU4061", "MATH GU4062", "COMS W4111",
           "COMS W4113", "COMS W4115", "COMS W4118", "COMS W4119", "COMS W4152",
           "COMS W4156", "COMS W4160", "COMS W4167", "COMS W4170", "COMS W4181",
           "CSOR E4231", "COMS W4236", "COMS W4701", "COMS W4705", "COMS W4731",
           "COMS W4733", "CBMF W4761", "COMS W4771", "CSEE W4824", "CSEE W4868"],
          50, count=2, credits=6,
          notes="Two 3-point electives in either computer science or mathematics."),
]

MATH_STAT_REQS = [
    _card("Mathematics (pick 5)", RequirementType.N_OF,
          ["MATH UN1101", "MATH UN1102", "MATH UN1201", "MATH UN2010", "MATH UN2500",
           "MATH UN1205", "MATH UN1207", "MATH UN1208"], 10, count=5, credits=15),
    _card("Introductory Statistics", RequirementType.ALL_OF, ["STAT UN1201"], 20, credits=3),
    _card("Statistics Required (pick 3)", RequirementType.N_OF,
          ["STAT GU4203", "STAT GU4204", "STAT GU4205"], 30, count=3, credits=9),
    _card("Statistics Elective (pick 1)", RequirementType.N_OF,
          ["STAT GU4207", "STAT GU4262", "STAT GU4264", "STAT GU4265"], 40,
          count=1, credits=3),
    _card("Computer Science (pick 1)", RequirementType.ONE_OF,
          ["COMS W1004", "COMS W1005", "ENGI E1006", "COMS W1007"], 50, credits=3),
]

# --- Sustainable Development -------------------------------------------------

SUSTDEV_MAJOR_REQS = [
    _card("Sustainable Development Foundation", RequirementType.ALL_OF,
          ["SDEV UN2300", "EESC UN2330"], 10, credits=7,
          notes="SDEV UN1900 is no longer required as of Fall 2023."),
    _card("Basic Disciplinary Foundation (pick 4)", RequirementType.N_OF,
          ["CHEM UN1403", "CHEM UN1404", "EEEB UN2001", "EEEB UN2002", "EESC UN1600",
           "EESC UN2100", "EESC UN2200", "EESC UN2300", "PHYS UN1201", "PHYS UN1202",
           "ANTH UN1002", "ANTH UN1003", "ANTH UN2004", "ECON UN1105", "HIST UN2222",
           "POLS UN1201", "POLS UN1501", "POLS UN1601", "SDEV UN2000", "SDEV UN2050",
           "SDEV UN3400", "SOCI UN1000", "EEEB UN3005", "STAT UN1101", "STAT UN1201",
           "MATH UN2015"], 20, count=4, credits=13,
          notes="One science sequence (labs required for Physics/EnvBio), two social "
                "science courses, and one quantitative foundations course."),
    _card("Analysis & Solutions to Complex Problems (pick 2)", RequirementType.N_OF,
          ["CIEE E3260", "EESC GU4600", "HIST UN3712", "HIST GU4811", "PUBH UN3100",
           "PUBH GU4200", "SDEV UN3355", "SDEV UN3360", "SDEV UN3366", "SDEV UN3410",
           "URBS UN3565", "SDEV GU4250", "SDEV GU4650", "SDEV GU4680"], 30,
          count=2, credits=6),
    _card("Skills / Actions (pick 2)", RequirementType.N_OF,
          ["EAEE E4257", "EESC GU4050", "SDEV UN2320", "SDEV UN3390", "SDEV UN3450",
           "SOCI UN3010", "SUMA PS4100", "SDEV GU4101"], 40, count=2, credits=6),
    _card("Electives (pick 3)", RequirementType.N_OF,
          ["SDEV UN3310", "SDEV GU4050", "SDEV GU4350", "SDEV GU4600", "SDEV GU4501",
           "SDEV GU4660", "SDEV GU4680", "SDEV GU4325", "SDEV GU4640", "SDEV GU4670"],
          50, count=3, credits=9),
    _card("Practicum (pick 1)", RequirementType.N_OF,
          ["SDEV GU4500", "SDEV GU4550", "SDEV UN3998", "SUMA PS4310"], 60,
          count=1, credits=3),
    _card("Capstone Workshop (pick 1)", RequirementType.N_OF,
          ["SDEV UN3280", "SDEV UN3550", "SDEV GU4400"], 70, count=1, credits=4,
          notes="A minimum of 15 courses + practicum, ~47 points total for the major."),
]

SUSTDEV_CONCENTRATION_REQS = [
    _card("Sustainable Development Foundation", RequirementType.ALL_OF,
          ["SDEV UN2300", "EESC UN2330"], 10, credits=7),
    _card("Natural Science Systems (pick 1)", RequirementType.N_OF,
          ["CHEM UN1403", "EEEB UN2001", "EESC UN1600", "EESC UN2100", "EESC UN2200",
           "EESC UN2300", "PHYS UN1201", "SDEV UN2000"], 20, count=1, credits=4),
    _card("Human Science Systems (pick 1)", RequirementType.N_OF,
          ["ANTH UN1002", "ANTH UN1003", "ANTH UN2004", "ECON UN1105", "HIST UN2222",
           "POLS UN1201", "POLS UN1501", "POLS UN1601", "SOCI UN1000", "SDEV UN2050"],
          30, count=1, credits=4),
    _card("Analysis & Solutions (pick 2)", RequirementType.N_OF,
          ["CIEE E3260", "EESC GU4600", "HIST UN3712", "PUBH UN3100", "SDEV UN3355",
           "SDEV UN3360", "SDEV UN3366", "SDEV UN3410", "URBS UN3565", "SDEV GU4250",
           "SDEV GU4650"], 40, count=2, credits=6),
    _card("Skills / Actions (pick 1)", RequirementType.N_OF,
          ["EAEE E4257", "EESC GU4050", "SDEV UN2320", "SDEV UN3390", "SDEV UN3450",
           "SOCI UN3010", "SDEV GU4101"], 50, count=1, credits=3),
    _card("Practicum (pick 1)", RequirementType.N_OF,
          ["SDEV GU4500", "SDEV GU4550", "SDEV UN3998", "SUMA PS4310"], 60,
          count=1, credits=3,
          notes="Special concentration: minimum 9 courses + practicum."),
]

# --- Philosophy ---------------------------------------------------------------

PHIL_MAJOR_REQS = [
    _card("History of Philosophy (pick 2)", RequirementType.N_OF,
          ["PHIL UN2101", "PHIL UN2201"], 10, count=2, credits=8,
          notes="History of Philosophy I and II."),
    _card("Symbolic Logic", RequirementType.ALL_OF, ["PHIL UN3411"], 20, credits=3),
    _card("Core Areas (pick 2)", RequirementType.N_OF,
          ["PHIL UN2702", "PHIL UN3701", "PHIL UN3751"], 30, count=2, credits=6,
          notes="Ethics / metaphysics / epistemology core options per the bulletin list."),
    _card("Majors Seminar", RequirementType.ALL_OF, ["PHIL UN3912"], 40, credits=3),
    _card("Philosophy Coursework (30 points)", RequirementType.CATEGORY_CREDITS,
          [], 50, credits=30, category="phil_ug",
          notes="Minimum 30 points in philosophy chosen from UN/GU-prefixed courses."),
]

PHIL_CONCENTRATION_REQS = [
    _card("Philosophy Coursework (24 points)", RequirementType.CATEGORY_CREDITS,
          [], 10, credits=24, category="phil_ug",
          notes="Minimum 24 points in philosophy (UN/GU); no specific required courses."),
]

MA_PHILOSOPHY_REQS = [
    _card("Graduate Philosophy Coursework (30 points)", RequirementType.CATEGORY_CREDITS,
          [], 10, credits=30, category="phil_grad",
          notes="CURATED — philosophy.columbia.edu blocks automated access; verify "
                "manually against the department's MA page. 30 points of graduate "
                "(4000+) philosophy coursework plus the MA essay under faculty "
                "supervision."),
    _card("Total: 30 points", RequirementType.CREDITS, [], 90, credits=30),
]

# --- English ------------------------------------------------------------------

ENGLISH_MAJOR_REQS = [
    _card("Introductory Course", RequirementType.ONE_OF,
          ["ENGL UN2000", "ENGL UN2001"], 10, credits=3,
          notes="Approaches to Literary Study (or Literary Texts and Critical Methods "
                "ENGL 3001/3011 where offered)."),
    _card("Literature Coursework (10 courses)", RequirementType.CATEGORY_CREDITS,
          [], 20, credits=30, category="english_lit",
          notes="At least 10 ENGL/CLEN courses (letter grade, C- or higher) including "
                "distribution: one course per genre (poetry, prose, drama/film/media); "
                "one per geography (British, American, Global/Comparative); three "
                "pre-1800 courses (max one Shakespeare). Distribution is verified "
                "manually — the engine counts points."),
]

ENGLISH_CONCENTRATION_REQS = [
    _card("Introductory Course", RequirementType.ONE_OF,
          ["ENGL UN2000", "ENGL UN2001"], 10, credits=3),
    _card("Literature Coursework (8 courses)", RequirementType.CATEGORY_CREDITS,
          [], 20, credits=24, category="english_lit",
          notes="8 ENGL/CLEN courses with reduced distribution (two genres, two "
                "geographies, two pre-1800) — verified manually."),
]


MORE_PROGRAMS: dict[str, list[dict]] = {
    "columbia_econ_financial": FINANCIAL_ECON_REQS,
    "columbia_econ_math": ECON_MATH_REQS,
    "columbia_econ_polisci": ECON_POLISCI_REQS,
    "columbia_econ_stat": ECON_STAT_REQS,
    "columbia_econ_philosophy": ECON_PHILOSOPHY_REQS,
    "columbia_math_major": MATH_MAJOR_REQS,
    "columbia_math_concentration": MATH_CONCENTRATION_REQS,
    "columbia_applied_math_major": APPLIED_MATH_REQS,
    "columbia_math_minor": MATH_MINOR_REQS,
    "columbia_math_prob_minor": MATH_PROB_MINOR_REQS,
    "columbia_cs_math": CS_MATH_REQS,
    "columbia_math_stat": MATH_STAT_REQS,
    "columbia_sustdev_major": SUSTDEV_MAJOR_REQS,
    "columbia_sustdev_concentration": SUSTDEV_CONCENTRATION_REQS,
    "columbia_phil_major": PHIL_MAJOR_REQS,
    "columbia_phil_concentration": PHIL_CONCENTRATION_REQS,
    "columbia_ma_philosophy": MA_PHILOSOPHY_REQS,
    "columbia_english_major": ENGLISH_MAJOR_REQS,
    "columbia_english_concentration": ENGLISH_CONCENTRATION_REQS,
}

MORE_LABELS: dict[str, str] = {
    "columbia_econ_financial": "Financial Economics Major",
    "columbia_econ_math": "Economics-Mathematics Major",
    "columbia_econ_polisci": "Economics-Political Science Major",
    "columbia_econ_stat": "Economics-Statistics Major",
    "columbia_econ_philosophy": "Economics-Philosophy Major",
    "columbia_math_major": "Mathematics Major",
    "columbia_math_concentration": "Mathematics Concentration",
    "columbia_applied_math_major": "Applied Mathematics Major",
    "columbia_math_minor": "Mathematics Minor",
    "columbia_math_prob_minor": "Mathematical Probability Minor",
    "columbia_cs_math": "Computer Science–Mathematics Major",
    "columbia_math_stat": "Mathematics-Statistics Major",
    "columbia_sustdev_major": "Sustainable Development Major",
    "columbia_sustdev_concentration": "Sustainable Development Concentration",
    "columbia_phil_major": "Philosophy Major",
    "columbia_phil_concentration": "Philosophy Concentration",
    "columbia_ma_philosophy": "MA in Philosophy",
    "columbia_english_major": "English Major",
    "columbia_english_concentration": "English Concentration",
}
