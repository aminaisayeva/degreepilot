# DegreePilot

> Agentic academic planning that *validates*, not just chats.
>
> **LLMs explain and interact. The planning engine validates.**

DegreePilot is a portfolio-grade, full-stack project that turns degree
requirements, prerequisite chains, course metadata, workload scoring, and a
student's career goals into a validated 4-year plan — with three strategy
variants, deterministic audit, a tool-using advisor, and an interactive
prerequisite graph.

The MVP covers two Columbia programs with curated sample data:

- **BA in Computer Science** (Columbia College) — Core Curriculum + CS major,
  with an optional Economics concentration.
- **MS in Computer Science** (SEAS) — 30-point graduate program with breadth
  areas, track depth, and graduate electives. Undergraduate prerequisites are
  treated as satisfied (a CS bachelor's is assumed for admission). All ten
  official pathways are modeled as their own programs (Machine Learning, NLP,
  Computer Security, Software Systems, Network Systems, Computational
  Biology, Foundations of CS, Vision/Graphics/Interaction/Robotics, plus the
  invite-only Personalized and Thesis pathways), each with its scraped
  fundamental/secondary course lists and the department's research-credit
  rules.

```
                    ┌──────────────────────────────────────────────────────┐
                    │                     DegreePilot                      │
                    │                                                      │
   student form ───►│  Audit → Planner → Validator → Comparator → Advisor  │
                    │     (deterministic Python, ~no LLM in the loop)      │
                    └──────────────────────────────────────────────────────┘
                                              │
                                              ▼
                            React UI · React Flow graph · chat
```

---

## Why this exists

Most "AI advisor" products are ChatGPT wrappers that *guess* prerequisites and
*invent* course codes. That model breaks the moment a real student trusts it
for graduation planning.

DegreePilot inverts that pattern:

- **Prerequisites, audits, validation, and plan generation are deterministic
  Python.** They run in milliseconds and never hallucinate.
- **The advisor is a tool-using layer.** Every reply calls real planning
  functions (`audit_student`, `validate_plan`, `career_track_picks`) and then
  explains the results. The MVP uses templated explanations; a real LLM
  provider can be plugged in behind the same `LLMProvider` interface without
  touching the validator.

This separation is the product thesis and the architectural backbone.

---

## What's in the MVP

### Student journey

1. **Landing page** — one-click demos: *Alex Demo* (BA CS + Econ sophomore)
   or *Maya Demo* (first-year MS in CS).
2. **Onboarding** — 4-step flow (basics → completed courses → workload
   preferences → career goals), with a degree picker (BA vs. MS) that scopes
   requirements, presets, and planning to your program.
3. **Dashboard** — degree audit cards per requirement, with progress bars,
   completed/missing course chips, credit counts, and warnings.
4. **Planner** — generates three plan variants (Balanced, Career-Optimized,
   Early-Graduation), shows a horizontal semester timeline with workload
   badges, displays every validator warning, and exports to Markdown or JSON.
5. **Course explorer** — full catalog with search, career-tag and term
   filters, plus a detail panel that renders prereqs in CNF (`(A OR B) AND
   C`).
6. **Prereq graph** — React Flow with three view modes: *Current plan*,
   *AI/ML track*, *Everything*. Completed courses are highlighted.
7. **Advisor chat** — six built-in intents (graduation feasibility, missing
   requirements, study-abroad impact, AI/ML picks, recommendation rationale,
   plan risk). Each message shows the deterministic tool calls used to
   produce the answer.
8. **Plan comparison** — side-by-side cards with feasibility, career
   alignment, workload variance, term skeleton, and a recommended winner
   with rationale.

### Engines

| Module | What it does |
|---|---|
| `prereq_graph` | CNF prereqs (list of OR-groups), depth computation, unlock map. |
| `audit` | Per-requirement progress for `all_of`, `one_of`, `n_of`, `category_credits`, `credits`. |
| `validator` | Prereq violations, credit caps, term offerings, duplicates, workload, unmet graduation. |
| `generator` | Three strategies; spreads requirements across the horizon; respects prereqs; weights by career goals. |
| `scorers` | Workload per term (credits × difficulty), career alignment (fraction of weighted hits), variance. |
| `comparator` | Ranks plans on errors → completeness → career alignment → variance → length. |
| `ai/advisor` | Intent classifier + deterministic tool calls + provider-abstracted explanation. |

### Backend endpoints

```
GET  /health
GET  /courses[?q=&category=&career_tag=&term=]
GET  /courses/{code}
GET  /requirements/{program}
POST /students
GET  /students
GET  /students/{id}
PUT  /students/{id}
GET  /students/{id}/audit[?program=]
POST /plans/generate     { student_id, strategies[] }   # balanced | career_optimized | aggressive (alias: early_graduation)
POST /plans/validate     { student_id, plan }
POST /plans/compare      { student_id, plans[] }
POST /advisor/chat       { student_id, message, plan_id? }
POST /advisor/v2/chat    { student_id, message, plan_id? }   # multi-agent trace
POST /admin/sync?term=Fall2026[&subjects=…&wait=true]        # live directory refresh
GET  /admin/sync/status
GET  /admin/accuracy          # human verification dashboard (HTML)
GET  /admin/accuracy/data
POST /admin/accuracy/check    { entity_type, entity_key, status, notes }
```

---

## Catalog data pipeline

The catalog is built from **committed scrape snapshots merged with a curated
overlay** — no runtime scraping, and curated knowledge is never overwritten:

```
scripts/scrape_catalog.py  (one-shot, manual)
  bulletin.columbia.edu   → titles, credits, descriptions, requirement lists
  doc.sis.columbia.edu    → term offerings, credits
        │
        ▼
app/seed/data/*.json       raw snapshots (source_url + scraped_at provenance)
app/seed/overlays/*.py     curated CNF prereqs, categories, career tags, workload
        │
        ▼
app/seed/loader.py         merge (curated wins) + derived elective categories
app/seed/expand.py         "_dynamic" requirements (e.g. any COMS 3000+) +
                           hard validation: every requirement course must exist
        │
        ▼
seed_all()                 ~1,945 courses + 204 requirements across 37 programs
                           (CS/Econ/Data Science/Math/Applied Math/Sustainable
                           Development/Philosophy/English majors, five Econ
                           joint majors, CS-Math and Math-Stat joints, the ten
                           MS CS pathways, the MA in Philosophy, and each
                           department's concentrations/minors)
                           (CC Science A/B/C structure; 10 MS pathway programs
                           scraped from cs.columbia.edu with research-credit
                           policy — max 12 research points, ≤3 of E6901,
                           thesis pathway = 9 points of E6902)
```

- Refresh the snapshots any time with
  `python -m scripts.scrape_catalog` (from `apps/api`, venv active).
- **Accuracy dashboard:** open `http://localhost:8000/admin/accuracy` to
  verify every program → requirement → course against the official Bulletin
  and Directory sources (links per row), mark rows verified/incorrect with
  notes, and track per-program accuracy. Checks persist in the database.

---

## Architecture

```
degreepilot/
  apps/
    web/                  # React + Vite + TS + Tailwind frontend
    api/                  # FastAPI + SQLModel backend
      app/
        api/routes/       # FastAPI routers
        core/             # config, db, term utilities
        models/           # SQLModel ORM tables
        schemas/          # Pydantic I/O schemas
        services/
          audit/          # deterministic auditor
          planner/        # prereq graph, generator, validator,
                          # comparator, scorers
          ai/             # advisor + LLM provider abstraction
        seed/             # Columbia CS + Econ sample data + demo student
      tests/              # pytest engines + advisor
  packages/
    shared/               # mirrored TS types (single source of truth)
  docker-compose.yml      # Postgres + API + Web
```

### Tech choices

- **Backend:** FastAPI, SQLModel, Pydantic v2, SQLite by default (zero-setup
  demo) with Postgres as the production path.
- **Frontend:** React 18, Vite 5, TypeScript, Tailwind 3, TanStack Query 5,
  Zustand 4 (persisted), React Flow 11, Lucide icons.
- **Why no LLM provider in MVP:** the validator should be the source of truth;
  the chat is templated until a real provider is wired in.

---

## Run locally

You can run the MVP in two minutes without Docker.

### 1. Backend

```bash
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The app boots, creates a SQLite DB (`degreepilot.db`), seeds ~1,077 courses
(scraped Columbia Bulletin + Directory snapshots merged with the curated
overlay) + requirements across 4 programs (Core Curriculum, CS major, Econ
concentration, MS in CS), and inserts two pre-built demo students.

- API: http://localhost:8000
- Docs (Swagger): http://localhost:8000/docs

### 2. Frontend

```bash
cd apps/web
npm install
npm run dev
```

- Web: http://localhost:5173

The dev server proxies `/api` → `http://localhost:8000`. Override with
`VITE_API_URL` if your API runs elsewhere.

### Or use Docker

```bash
docker compose up --build
```

Brings up Postgres + API + Web (Postgres URL configured automatically).

---

## Test

```bash
cd apps/api
. .venv/bin/activate
pytest
```

98 backend tests cover prereq graph, auditor, planner (3 strategies, both
degree levels), validator (prereqs, credits, duplicates, term offerings),
scorers, comparator, advisor intents, the bulletin/directory parsers, the
snapshot loader + dynamic requirement expansion, and the accuracy endpoints.

The frontend type-checks with `npm run lint` and builds with `npm run build`.

---

## 3-minute demo script

1. **Open `/`** — show the landing. Click *Try the demo student*.
2. **Dashboard** — point at the audit cards: 4/13 requirements satisfied,
   credits counter, warnings panel.
3. **Click "Generate plans"** — flip through *Balanced*, *Career-Optimized*,
   *Early-Graduation* in the planner. Notice the workload badges per term and
   the validator's footer warnings.
4. **Export** — click `.md` to show the live Markdown export.
5. **Open `/graph`** — switch to *AI/ML track*; trace the prereq chain from
   COMS3134 → COMS4771 → COMS4705.
6. **Open `/advisor`** — click *"Can I graduate on time?"*. Highlight the
   `audit_student` tool-call chip under the answer. Then click *"What's the
   risk in this plan?"* — show the `validate_plan` tool call.
7. **Open `/compare`** — point at the winner card and the rationale line.

---

## Technical highlights

- **CNF prerequisite model.** Prereqs are stored as a list of OR-groups so
  `(COMS1004 OR COMS1006) AND COMS3203` survives normalization. The validator
  and generator both reason against it.
- **Three real strategies.** The generator is greedy with strategy-specific
  scoring: balanced spreads credits over the full horizon, career-optimized
  front-loads career-aligned courses, early-graduation packs to the credit
  cap. Each plan is run through the validator and gets attached warnings.
- **Audit and validator share types.** The audit and validator both consume
  the same `Requirement` and `Course` models so the planner can simulate a
  future audit (`"what does the audit look like *if* this plan completes?"`).
- **Tool-using advisor.** Every advisor response surfaces the tool name and a
  preview of its output — the user can see exactly what the engine returned
  before the explanation rephrased it. The provider interface allows swapping
  the templated explainer for any hosted LLM API without touching the validator.
- **React Flow with computed depth layout.** The graph computes per-node
  prereq depth on the focused subgraph and lays out columns left-to-right.

---

## Roadmap

- ~~Real Columbia Bulletin import (one-shot offline crawl + curation step).~~
  ✅ Shipped — see *Catalog data pipeline* above.
- Vector search over course descriptions for "courses like X" advisor intent.
- Plug-in hosted LLM provider behind the existing `LLMProvider` interface
  for richer explanations while the validator stays authoritative.
- Multi-program support (engineering core, additional minors, double majors).
- Persisted plans + share links.
- Authentication and student accounts.

---

## Resume bullets

- Designed and built **DegreePilot**, a full-stack academic planning platform
  (FastAPI + React + Postgres) that generates and validates 4-year degree
  plans for Columbia CS + Econ using a deterministic planning engine and a
  tool-using AI advisor (32 backend tests, ~3.5 k LOC).
- Implemented a **CNF prerequisite graph**, a multi-strategy plan generator
  (balanced / career-optimized / early-graduation), and a degree audit engine
  that supports `all_of`, `one_of`, `n_of`, and category-credit requirements.
- Built a **tool-using advisor** with a provider-abstracted `LLMProvider`
  interface so deterministic planning functions remain the source of truth
  while explanations can be swapped between templated and real-LLM backends.
- Shipped a polished UI: React Flow prereq graph, semester timeline,
  side-by-side plan comparison, Markdown/JSON export, and a 4-step
  onboarding flow.

---

## Disclaimer

**Sample data.** The course catalog, prerequisite chains, and degree
requirements are curated to be realistic for the Columbia CS + Econ minor
context but are not an official catalog representation. Do not use to make
real registration decisions.
