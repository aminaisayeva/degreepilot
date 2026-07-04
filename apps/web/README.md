# DegreePilot Web

React + TypeScript + Vite + Tailwind + shadcn-style primitives. Talks to the
FastAPI backend in [../api](../api).

## Run

```bash
cd apps/web
npm install
npm run dev
```

Visit http://localhost:5173. The dev server proxies `/api` → `http://localhost:8000`,
so set `VITE_API_URL` only if your API is elsewhere.

## Stack

- **React 18 + Vite 5** for the dev/build pipeline.
- **TailwindCSS 3** with hand-written shadcn-style primitives (`Card`, `Button`,
  `Badge`, `Progress`, `Tabs`).
- **TanStack Query** for server state, **Zustand** (with `persist`) for the
  selected student + active plan.
- **React Flow** for the prerequisite graph visualization.
- **Lucide** for icons.

## Pages

- `/` — Landing (with one-click demo student loader)
- `/onboarding` — 4-step student profile
- `/dashboard` — Degree audit cards + warnings
- `/planner` — Plan timeline + variant tabs + export
- `/courses` — Catalog explorer with filters
- `/graph` — Interactive prerequisite graph
- `/advisor` — Tool-using advisor chat
- `/compare` — Side-by-side plan comparison
