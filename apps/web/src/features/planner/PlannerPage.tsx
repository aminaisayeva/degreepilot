import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  Download,
  FileJson,
  FileText,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Progress } from "@/components/ui/Progress";
import { Tabs } from "@/components/ui/Tabs";
import { exportPlanAsJSON, exportPlanAsMarkdown } from "@/features/planner/export";
import { api } from "@/lib/api";
import { nextTermWithSummer, termsAfter, termsSpan } from "@/lib/terms";
import { cn, formatPct, workloadLabel } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { Course, Plan, PlanWarning } from "@/types/api";

export function PlannerPage() {
  const navigate = useNavigate();
  const studentId = useSession((s) => s.studentId);
  const plans = useSession((s) => s.plans);
  const setPlans = useSession((s) => s.setPlans);
  const activeIdx = useSession((s) => s.activePlanIndex);
  const setActiveIdx = useSession((s) => s.setActivePlanIndex);

  const { data: courses } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.listCourses(),
  });
  const catalog = useMemo(() => {
    const m = new Map<string, Course>();
    (courses ?? []).forEach((c) => m.set(c.code, c));
    return m;
  }, [courses]);

  const generate = useMutation({
    mutationFn: async () => {
      if (!studentId) throw new Error("No student in session.");
      return api.generatePlans(studentId, ["balanced", "career_optimized", "aggressive"]);
    },
    onSuccess: setPlans,
  });

  const { data: student } = useQuery({
    queryKey: ["student", studentId],
    enabled: !!studentId,
    queryFn: () => api.getStudent(studentId!),
  });

  const [editing, setEditing] = useState(false);

  const updateActivePlan = (next: Plan) => {
    setPlans(plans.map((p, i) => (i === activeIdx ? next : p)));
  };

  const validate = useMutation({
    mutationFn: async (p: Plan) => {
      if (!studentId) throw new Error("No student in session.");
      return api.validatePlan(studentId, p);
    },
    onSuccess: (res, p) => {
      updateActivePlan({ ...p, warnings: res.warnings });
    },
  });

  const startManualPlan = () => {
    if (!student) return;
    const includeSummer = !(((student.constraints as Record<string, unknown>)?.no_summer as boolean | undefined) ?? true);
    const terms = termsSpan(student.current_term, student.graduation_term, includeSummer);
    const manual: Plan = {
      student_id: student.id,
      name: "Manual Plan",
      strategy: "manual",
      terms: terms.map((t) => ({ term: t, courses: [], total_credits: 0, workload_score: 0 })),
      warnings: [],
      summary: { program: student.programs[0] ?? "columbia_cs_major", strategy: "manual" },
    };
    setPlans([...plans, manual]);
    setActiveIdx(plans.length);
    setEditing(true);
  };

  if (!studentId) {
    return <NoStudent />;
  }

  const plan = plans[activeIdx];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Plan generator</h1>
          <p className="text-sm text-muted">
            Three deterministic strategies — no LLM in the loop. Pin or avoid courses
            below, pick a strategy, and read every warning the engine raised.
          </p>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate("/dashboard")}>Back to dashboard</Button>
          <Button onClick={startManualPlan} disabled={!student}>
            Manual plan
          </Button>
          <Button
            variant="primary"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          >
            <Sparkles className="h-4 w-4" />
            {generate.isPending
              ? "Generating…"
              : plans.length
              ? "Regenerate"
              : "Generate plans"}
          </Button>
        </div>
      </header>

      <PlanPreferences
        studentId={studentId}
        courses={courses ?? []}
        onSaved={() => generate.mutate()}
      />

      {generate.isError && (
        <div className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          Plan generation failed: {(generate.error as Error).message}
        </div>
      )}

      {plans.length === 0 && (
        <Card>
          <CardBody className="text-center">
            <div className="mx-auto grid h-10 w-10 place-items-center rounded-xl bg-accent/15 text-accent">
              <Workflow className="h-5 w-5" />
            </div>
            <div className="mt-3 text-base font-semibold">No plans yet</div>
            <div className="mt-1 text-sm text-muted">
              Click <span className="font-semibold text-ink">Generate plans</span> to produce
              three variants — Balanced, Career-Optimized, and Early-Graduation.
            </div>
          </CardBody>
        </Card>
      )}

      {plans.length > 0 && plan && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Tabs
              value={String(activeIdx)}
              onChange={(v) => setActiveIdx(parseInt(v, 10))}
              options={plans.map((p, i) => ({
                value: String(i),
                label: <span className="px-1">{p.name}</span>,
              }))}
            />
            <Button onClick={() => setEditing(!editing)}>
              {editing ? "Done editing" : "Edit plan"}
            </Button>
            <Button
              onClick={() => validate.mutate(plan)}
              disabled={validate.isPending}
            >
              {validate.isPending ? "Validating…" : "Validate"}
            </Button>
            <Button onClick={() => navigate("/compare")}>
              Compare <ChevronRight className="h-4 w-4" />
            </Button>
            <div className="ml-auto flex gap-2">
              <Button onClick={() => exportPlanAsMarkdown(plan)}>
                <FileText className="h-4 w-4" /> .md
              </Button>
              <Button onClick={() => exportPlanAsJSON(plan)}>
                <FileJson className="h-4 w-4" /> .json
              </Button>
            </div>
          </div>

          <PlanSummary plan={plan} />
          {editing ? (
            <PlanEditor
              plan={plan}
              catalog={catalog}
              courses={courses ?? []}
              onChange={updateActivePlan}
            />
          ) : (
            <PlanTimeline plan={plan} catalog={catalog} />
          )}
          <PlanWarnings warnings={plan.warnings} />
        </>
      )}
    </div>
  );
}

function PlanSummary({ plan }: { plan: Plan }) {
  const errs = plan.warnings.filter((w) => w.severity === "error").length;
  const warns = plan.warnings.filter((w) => w.severity === "warning").length;
  const completion = (plan.summary?.post_plan_completion_pct as number) ?? 0;
  const career = (plan.summary?.career_alignment as number) ?? 0;
  const variance = (plan.summary?.workload_variance as number) ?? 0;
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
      <Stat label="Strategy" value={plan.summary?.strategy ?? plan.strategy} />
      <Stat label="Terms used" value={plan.summary?.terms_used ?? plan.terms.length} />
      <Stat label="Graduation" value={plan.summary?.graduation_term ?? ""} />
      <Stat label="Career alignment" value={formatPct(career)} accent />
      <Stat
        label="Plan health"
        value={
          errs ? `${errs} blockers` : warns ? `${warns} warnings` : "All clear"
        }
        tone={errs ? "danger" : warns ? "warn" : "ok"}
      />
      <div className="card card-pad col-span-2 md:col-span-5">
        <div className="mb-2 flex items-center justify-between text-xs text-muted">
          <span>Coverage after plan</span>
          <span>{formatPct(completion)}</span>
        </div>
        <Progress value={completion} />
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-muted md:grid-cols-4">
          <div>Total credits planned: <span className="text-ink">{plan.summary?.total_credits ?? "—"}</span></div>
          <div>Workload variance: <span className="text-ink">{variance}</span></div>
          <div>Unmet reqs: <span className="text-ink">{(plan.summary?.unmet_requirements as string[] | undefined)?.length ?? 0}</span></div>
          <div>Plan name: <span className="text-ink">{plan.name}</span></div>
        </div>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  accent,
}: {
  label: string;
  value: string | number;
  tone?: "ok" | "warn" | "danger";
  accent?: boolean;
}) {
  const toneCls = tone === "ok" ? "text-ok" : tone === "warn" ? "text-warn" : tone === "danger" ? "text-danger" : accent ? "text-accent" : "";
  return (
    <div className="card card-pad">
      <div className="text-xs text-muted">{label}</div>
      <div className={cn("mt-1 text-lg font-semibold", toneCls)}>{value as any}</div>
    </div>
  );
}

function PlanTimeline({ plan, catalog }: { plan: Plan; catalog: Map<string, Course> }) {
  return (
    <div className="overflow-x-auto">
      <div className="flex min-w-full gap-3 pb-2">
        {plan.terms.map((t, i) => {
          const tone =
            t.workload_score >= 17 ? "danger" : t.workload_score >= 14 ? "warn" : "ok";
          return (
            <div key={i} className="card card-pad w-72 shrink-0">
              <div className="flex items-center justify-between">
                <div className="font-semibold">{t.term}</div>
                <Badge variant={tone}>{t.workload_score} load</Badge>
              </div>
              <div className="mt-1 text-xs text-muted">
                {t.total_credits} credits · {t.courses.length} courses
              </div>
              <div className="mt-3 space-y-2">
                {t.courses.map((code) => (
                  <PlanCourseCard
                    key={code}
                    code={code}
                    course={catalog.get(code)}
                    catalogReady={catalog.size > 0}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PlanCourseCard({
  code,
  course,
  catalogReady,
}: {
  code: string;
  course: Course | undefined;
  catalogReady: boolean;
}) {
  const [open, setOpen] = useState(false);

  if (!course) {
    return (
      <div className="rounded-xl border border-border bg-elevated p-3">
        <div className="font-mono text-xs text-accent">{code}</div>
        <div className="mt-1 text-xs text-muted">
          {catalogReady ? "Not in the current catalog — regenerate plans." : "Loading catalog…"}
        </div>
      </div>
    );
  }

  const prereqText =
    course.prerequisites.length === 0
      ? "None"
      : course.prerequisites.map((g) => `(${g.join(" OR ")})`).join(" AND ");

  return (
    <button
      onClick={() => setOpen((v) => !v)}
      className={cn(
        "w-full rounded-xl border bg-elevated p-3 text-left transition hover:border-accent/40",
        open ? "border-accent/60" : "border-border",
      )}
    >
      <div className="flex items-center justify-between">
        <div className="font-mono text-xs text-accent">{code}</div>
        <div className="text-[11px] text-muted">{course.credits} cr</div>
      </div>
      <div className="mt-1 text-sm text-ink">{course.title}</div>

      <div className="mt-2 flex flex-wrap gap-1">
        <Badge>{workloadLabel(course.workload_level)}</Badge>
        {(open ? course.career_tags : course.career_tags.slice(0, 2)).map((t) => (
          <Badge key={t} variant="accent">
            {t}
          </Badge>
        ))}
        {!open && course.career_tags.length > 2 && (
          <Badge>+{course.career_tags.length - 2}</Badge>
        )}
      </div>

      {open && (
        <div className="mt-3 space-y-2 border-t border-border pt-2">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted">Offered</div>
            <div className="mt-0.5 text-[11px] text-ink">
              {course.offered_terms.join(" · ")}
            </div>
          </div>
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted">Prerequisites</div>
            <div className="mt-0.5 text-[11px] text-ink">{prereqText}</div>
          </div>
        </div>
      )}
    </button>
  );
}

function PlanWarnings({ warnings }: { warnings: PlanWarning[] }) {
  if (!warnings.length) {
    return (
      <Card>
        <CardBody className="flex items-center gap-2 text-sm text-ok">
          <CheckCircle2 className="h-4 w-4" />
          No structural issues — every prereq lines up, all terms feasible.
        </CardBody>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Validation</CardTitle>
      </CardHeader>
      <CardBody className="space-y-2">
        {warnings.map((w, i) => (
          <div
            key={i}
            className={cn(
              "flex items-start gap-2 rounded-xl border p-3 text-sm",
              w.severity === "error"
                ? "border-danger/40 bg-danger/10 text-danger"
                : w.severity === "warning"
                ? "border-warn/40 bg-warn/10 text-warn"
                : "border-border bg-elevated text-muted",
            )}
          >
            <AlertTriangle className="mt-0.5 h-4 w-4" />
            <div>
              <div className="font-mono text-[11px] uppercase tracking-wide opacity-70">
                {w.code}{w.term ? ` · ${w.term}` : ""}{w.course ? ` · ${w.course}` : ""}
              </div>
              <div>{w.message}</div>
            </div>
          </div>
        ))}
      </CardBody>
    </Card>
  );
}

function NoStudent() {
  const navigate = useNavigate();
  return (
    <Card>
      <CardBody className="text-center">
        <div className="text-base font-semibold">No student selected.</div>
        <Button
          variant="primary"
          className="mt-3"
          onClick={() => navigate("/")}
        >
          Pick a student
        </Button>
      </CardBody>
    </Card>
  );
}

function PlanPreferences({
  studentId,
  courses,
  onSaved,
}: {
  studentId: number;
  courses: Course[];
  onSaved: () => void;
}) {
  const qc = useQueryClient();
  const { data: student } = useQuery({
    queryKey: ["student", studentId],
    queryFn: () => api.getStudent(studentId),
  });

  const constraints = (student?.constraints ?? {}) as Record<string, unknown>;
  const pins = (constraints.pinned_courses ?? []) as { code: string; term?: string | null }[];
  const avoids = (constraints.avoid_courses ?? []) as string[];

  const [pinQuery, setPinQuery] = useState("");
  const [pinTerm, setPinTerm] = useState<string>("");
  const [avoidQuery, setAvoidQuery] = useState("");

  const termOptions = useMemo(() => {
    if (!student) return [];
    const horizon = [student.current_term, ...termsAfter(student.current_term, 9)];
    const gradIdx = horizon.indexOf(student.graduation_term);
    return gradIdx >= 0 ? horizon.slice(0, gradIdx + 1) : horizon;
  }, [student]);

  const matches = (q: string) => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    return courses
      .filter(
        (c) =>
          c.code.toLowerCase().includes(query) || c.title.toLowerCase().includes(query),
      )
      .slice(0, 6);
  };

  const save = useMutation({
    mutationFn: (next: Record<string, unknown>) =>
      api.updateStudent(studentId, { constraints: { ...constraints, ...next } } as never),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["student", studentId] });
      onSaved();
    },
  });

  if (!student) return null;

  return (
    <details className="card">
      <summary className="card-pad cursor-pointer text-sm font-semibold">
        Plan preferences{" "}
        <span className="font-normal text-muted">
          — {pins.length} pinned · {avoids.length} avoided · deterministic, applied on
          regenerate
        </span>
      </summary>
      <div className="card-pad grid gap-4 border-t border-border md:grid-cols-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">
            Pin courses (must appear in the plan)
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {pins.map((p) => (
              <Badge
                key={p.code}
                variant="accent"
                className="cursor-pointer"
                onClick={() =>
                  save.mutate({ pinned_courses: pins.filter((x) => x.code !== p.code) })
                }
              >
                {p.code}
                {p.term ? ` @ ${p.term}` : ""} ✕
              </Badge>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            <input
              className="input"
              placeholder="Search course to pin…"
              value={pinQuery}
              onChange={(e) => setPinQuery(e.target.value)}
            />
            <select
              className="input w-40"
              value={pinTerm}
              onChange={(e) => setPinTerm(e.target.value)}
            >
              <option value="">Any term</option>
              {termOptions.map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="mt-1 space-y-1">
            {matches(pinQuery).map((c) => (
              <button
                key={c.code}
                className="block w-full rounded-lg border border-border bg-elevated px-2 py-1 text-left text-xs hover:border-accent/40"
                onClick={() => {
                  setPinQuery("");
                  save.mutate({
                    pinned_courses: [
                      ...pins.filter((x) => x.code !== c.code),
                      { code: c.code, term: pinTerm || null },
                    ],
                  });
                }}
              >
                <span className="font-mono text-accent">{c.code}</span> {c.title}
              </button>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">
            Avoid courses (skipped when alternatives exist)
          </div>
          <div className="mt-2 flex flex-wrap gap-1">
            {avoids.map((code) => (
              <Badge
                key={code}
                className="cursor-pointer"
                onClick={() =>
                  save.mutate({ avoid_courses: avoids.filter((x) => x !== code) })
                }
              >
                {code} ✕
              </Badge>
            ))}
          </div>
          <input
            className="input mt-2"
            placeholder="Search course to avoid…"
            value={avoidQuery}
            onChange={(e) => setAvoidQuery(e.target.value)}
          />
          <div className="mt-1 space-y-1">
            {matches(avoidQuery).map((c) => (
              <button
                key={c.code}
                className="block w-full rounded-lg border border-border bg-elevated px-2 py-1 text-left text-xs hover:border-accent/40"
                onClick={() => {
                  setAvoidQuery("");
                  save.mutate({ avoid_courses: [...new Set([...avoids, c.code])] });
                }}
              >
                <span className="font-mono text-accent">{c.code}</span> {c.title}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-muted">
            Mandatory (all-of) requirements can't be avoided — the engine keeps them and
            says so in the plan warnings.
          </p>
        </div>
      </div>
    </details>
  );
}

function recomputeTerm(term: string, codes: string[], catalog: Map<string, Course>) {
  const cs = codes.map((c) => catalog.get(c)).filter(Boolean) as Course[];
  return {
    term,
    courses: codes,
    total_credits: Math.round(cs.reduce((s, c) => s + c.credits, 0) * 100) / 100,
    // Mirrors the engine: sum of workload_level * credits/3.
    workload_score:
      Math.round(cs.reduce((s, c) => s + c.workload_level * (c.credits / 3), 0) * 100) / 100,
  };
}

function PlanEditor({
  plan,
  catalog,
  courses,
  onChange,
}: {
  plan: Plan;
  catalog: Map<string, Course>;
  courses: Course[];
  onChange: (p: Plan) => void;
}) {
  const [queries, setQueries] = useState<Record<number, string>>({});

  const setTermCourses = (idx: number, codes: string[]) => {
    const terms = plan.terms.map((t, i) =>
      i === idx ? recomputeTerm(t.term, codes, catalog) : t,
    );
    onChange({ ...plan, terms });
  };

  const addTerm = () => {
    const last = plan.terms[plan.terms.length - 1]?.term;
    const next = last ? nextTermWithSummer(last) : "Fall 2026";
    onChange({ ...plan, terms: [...plan.terms, recomputeTerm(next, [], catalog)] });
  };

  const removeTerm = (idx: number) => {
    onChange({ ...plan, terms: plan.terms.filter((_, i) => i !== idx) });
  };

  const inPlan = new Set(plan.terms.flatMap((t) => t.courses));

  const matches = (q: string, term: string) => {
    const query = q.trim().toLowerCase();
    if (query.length < 2) return [];
    const season = term.split(" ")[0];
    return courses
      .filter(
        (c) =>
          !inPlan.has(c.code) &&
          (c.code.toLowerCase().includes(query) || c.title.toLowerCase().includes(query)),
      )
      .sort((a, b) => {
        // Courses actually offered this season float to the top.
        const ao = a.offered_terms.includes(season) ? 0 : 1;
        const bo = b.offered_terms.includes(season) ? 0 : 1;
        return ao - bo || a.code.localeCompare(b.code);
      })
      .slice(0, 6);
  };

  return (
    <div className="space-y-2">
      <div className="rounded-xl border border-accent/40 bg-accent/10 p-3 text-xs">
        Editing mode — swap courses per semester, then hit{" "}
        <span className="font-semibold">Validate</span> to check the plan against your
        degree requirements (prereqs, offerings, credit caps, graduation coverage).
      </div>
      <div className="overflow-x-auto">
        <div className="flex min-w-full gap-3 pb-2">
          {plan.terms.map((t, i) => {
            const season = t.term.split(" ")[0];
            return (
              <div key={`${t.term}-${i}`} className="card card-pad w-72 shrink-0">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">{t.term}</div>
                  <button
                    className="text-xs text-muted hover:text-danger"
                    onClick={() => removeTerm(i)}
                    title="Remove semester"
                  >
                    remove
                  </button>
                </div>
                <div className="mt-1 text-xs text-muted">
                  {t.total_credits} credits · load {t.workload_score}
                </div>
                <div className="mt-3 space-y-1">
                  {t.courses.map((code) => {
                    const c = catalog.get(code);
                    const offered = !c?.offered_terms?.length || c.offered_terms.includes(season);
                    return (
                      <div
                        key={code}
                        className={cn(
                          "flex items-center justify-between rounded-lg border px-2 py-1 text-xs",
                          offered ? "border-border bg-elevated" : "border-warn/50 bg-warn/10",
                        )}
                      >
                        <div>
                          <span className="font-mono text-accent">{code}</span>
                          <span className="ml-1 text-muted">{c ? `· ${c.credits}cr` : ""}</span>
                          {!offered && (
                            <span className="ml-1 text-warn">not offered in {season}</span>
                          )}
                        </div>
                        <button
                          className="ml-2 text-muted hover:text-danger"
                          onClick={() => setTermCourses(i, t.courses.filter((x) => x !== code))}
                        >
                          ✕
                        </button>
                      </div>
                    );
                  })}
                </div>
                <input
                  className="input mt-2 text-xs"
                  placeholder="Add course…"
                  value={queries[i] ?? ""}
                  onChange={(e) => setQueries({ ...queries, [i]: e.target.value })}
                />
                <div className="mt-1 space-y-1">
                  {matches(queries[i] ?? "", t.term).map((c) => (
                    <button
                      key={c.code}
                      className="block w-full rounded-lg border border-border bg-elevated px-2 py-1 text-left text-xs hover:border-accent/40"
                      onClick={() => {
                        setQueries({ ...queries, [i]: "" });
                        setTermCourses(i, [...t.courses, c.code]);
                      }}
                    >
                      <span className="font-mono text-accent">{c.code}</span> {c.title}
                      <span className="ml-1 text-muted">
                        · {c.credits}cr{c.offered_terms.includes(t.term.split(" ")[0]) ? "" : " · not offered this season"}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
          <button
            className="card card-pad w-40 shrink-0 border-dashed text-sm text-muted hover:border-accent/40 hover:text-ink"
            onClick={addTerm}
          >
            + Add semester
          </button>
        </div>
      </div>
    </div>
  );
}
