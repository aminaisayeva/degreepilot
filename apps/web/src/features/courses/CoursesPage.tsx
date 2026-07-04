import { useQuery } from "@tanstack/react-query";
import { Filter, Search } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { cn, workloadLabel } from "@/lib/utils";
import type { Course } from "@/types/api";

const CAREER = ["ai_ml", "swe", "systems", "data", "quant", "security", "research", "product"];
const TERMS = ["Fall", "Spring"];

export function CoursesPage() {
  const [query, setQuery] = useState("");
  const [tag, setTag] = useState<string | null>(null);
  const [term, setTerm] = useState<string | null>(null);

  const { data: courses, isLoading } = useQuery({
    queryKey: ["courses", query, tag, term],
    queryFn: () =>
      api.listCourses({
        q: query || undefined,
        career_tag: tag || undefined,
        term: term || undefined,
      }),
  });

  const [selected, setSelected] = useState<Course | null>(null);
  const display = courses ?? [];
  const detail = selected ?? display[0];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Course catalog</h1>
        <p className="text-sm text-muted">
          Sample Columbia CS + Econ courses. Filter by career goal or term to plan a track.
        </p>
      </header>

      <div className="flex flex-wrap gap-2">
        <div className="relative grow">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
          <input
            className="input pl-9"
            placeholder="Search code, title, department…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-1 text-xs text-muted">
          <Filter className="h-4 w-4" /> Career
        </div>
        {CAREER.map((c) => (
          <FilterChip key={c} active={tag === c} onClick={() => setTag(tag === c ? null : c)}>
            {c}
          </FilterChip>
        ))}
        <div className="flex items-center gap-1 text-xs text-muted">Term</div>
        {TERMS.map((t) => (
          <FilterChip key={t} active={term === t} onClick={() => setTerm(term === t ? null : t)}>
            {t}
          </FilterChip>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <div className="lg:col-span-7 space-y-2">
          {isLoading && <div className="text-sm text-muted">Loading…</div>}
          {!isLoading && display.length === 0 && (
            <div className="rounded-xl border border-dashed border-border p-4 text-sm text-muted">
              No matches.
            </div>
          )}
          {display.map((c) => (
            <button
              key={c.code}
              onClick={() => setSelected(c)}
              className={cn(
                "card w-full text-left transition hover:border-accent/40",
                detail?.code === c.code && "border-accent/60",
              )}
            >
              <div className="card-pad">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="font-mono text-xs text-accent">{c.code}</div>
                    <div className="text-sm font-semibold">{c.title}</div>
                  </div>
                  <div className="text-right text-xs text-muted">
                    <div>{c.credits} cr</div>
                    <div>{workloadLabel(c.workload_level)}</div>
                  </div>
                </div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {(c.offered_terms ?? []).map((t) => (
                    <Badge key={t}>{t}</Badge>
                  ))}
                  {(c.career_tags ?? []).map((t) => (
                    <Badge key={t} variant="accent">
                      {t}
                    </Badge>
                  ))}
                </div>
              </div>
            </button>
          ))}
        </div>

        <div className="lg:col-span-5">
          <Card>
            <CardHeader>
              <CardTitle>Details</CardTitle>
            </CardHeader>
            <CardBody>
              {detail ? <CourseDetail c={detail} /> : <div className="text-sm text-muted">Pick a course.</div>}
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}

function FilterChip({
  children,
  active,
  onClick,
}: {
  children: React.ReactNode;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1 text-xs transition",
        active
          ? "border-accent bg-accent/15 text-accent"
          : "border-border bg-elevated text-muted hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function CourseDetail({ c }: { c: Course }) {
  return (
    <div className="space-y-3">
      <div>
        <div className="font-mono text-xs text-accent">{c.code}</div>
        <div className="text-lg font-semibold">{c.title}</div>
        <div className="text-xs text-muted">{c.department} · {c.credits} credits</div>
      </div>
      <p className="text-sm text-ink/90">{c.description}</p>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">Offered</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {(c.offered_terms ?? []).map((t) => (
            <Badge key={t}>{t}</Badge>
          ))}
        </div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">Prerequisites</div>
        <div className="mt-1 text-sm">
          {c.prerequisites.length === 0 ? (
            <span className="text-muted">None</span>
          ) : (
            c.prerequisites
              .map((g) => `(${g.join(" OR ")})`)
              .join(" AND ")
          )}
        </div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">Categories</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {(c.categories ?? []).map((t) => (
            <Badge key={t}>{t}</Badge>
          ))}
        </div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">Career tags</div>
        <div className="mt-1 flex flex-wrap gap-1">
          {(c.career_tags ?? []).map((t) => (
            <Badge key={t} variant="accent">
              {t}
            </Badge>
          ))}
        </div>
      </div>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-muted">Workload</div>
        <div className="text-sm">{workloadLabel(c.workload_level)} (level {c.workload_level}/5)</div>
      </div>
    </div>
  );
}
