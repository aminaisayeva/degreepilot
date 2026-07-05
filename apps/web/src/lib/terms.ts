// Semester arithmetic for the Fall/Spring planning calendar.

export function parseTerm(term: string): { season: "Fall" | "Spring"; year: number } {
  const [season, year] = term.split(" ");
  return { season: season as "Fall" | "Spring", year: Number(year) };
}

export function nextTerm(term: string): string {
  const { season, year } = parseTerm(term);
  return season === "Fall" ? `Spring ${year + 1}` : `Fall ${year}`;
}

/** The `count` semesters strictly after `from` (no same-term graduation —
 *  a plan horizon needs at least one future term). */
export function termsAfter(from: string, count: number): string[] {
  const out: string[] = [];
  let t = from;
  for (let i = 0; i < count; i++) {
    t = nextTerm(t);
    out.push(t);
  }
  return out;
}

/** Valid graduation choices for a start term: MS programs run 1-3 years,
 *  undergrad up to 5. */
export function gradTermOptions(currentTerm: string, degree: "undergrad" | "ms"): string[] {
  return termsAfter(currentTerm, degree === "ms" ? 6 : 10);
}

/** Default graduation pick: 4 semesters for MS (2 years max horizon is
 *  common), 8 for undergrad. */
export function defaultGradTerm(currentTerm: string, degree: "undergrad" | "ms"): string {
  const n = degree === "ms" ? 4 : 8;
  return termsAfter(currentTerm, n)[n - 1];
}

export function nextTermWithSummer(term: string): string {
  const [season, y] = term.split(" ");
  const year = Number(y);
  if (season === "Spring") return `Summer ${year}`;
  if (season === "Summer") return `Fall ${year}`;
  return `Spring ${year + 1}`;
}

/** All terms from `from` to `to` inclusive; summers included only on request. */
export function termsSpan(from: string, to: string, includeSummer: boolean): string[] {
  const out: string[] = [];
  let t = from;
  for (let guard = 0; guard < 24; guard++) {
    if (includeSummer || !t.startsWith("Summer")) out.push(t);
    if (t === to) break;
    t = nextTermWithSummer(t);
  }
  return out;
}
