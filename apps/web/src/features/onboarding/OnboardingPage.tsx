import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { defaultGradTerm, gradTermOptions } from "@/lib/terms";
import { cn } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { StudentCreate } from "@/types/api";

const STEPS = ["Basics", "Completed", "Workload", "Career"] as const;
type Step = (typeof STEPS)[number];

export type DegreeType = "undergrad" | "ms";

const UNDERGRAD_PROGRAMS = ["columbia_cc_core", "columbia_cs_major"];
const MS_PROGRAMS = ["columbia_ms_cs"];

const UNDERGRAD_MAJORS = [
  { slug: "columbia_cs_major", label: "Computer Science" },
  { slug: "columbia_econ_major", label: "Economics" },
  { slug: "columbia_econ_financial", label: "Financial Economics" },
  { slug: "columbia_econ_math", label: "Economics-Mathematics" },
  { slug: "columbia_econ_polisci", label: "Economics-Political Science" },
  { slug: "columbia_econ_stat", label: "Economics-Statistics" },
  { slug: "columbia_econ_philosophy", label: "Economics-Philosophy" },
  { slug: "columbia_data_science_major", label: "Data Science" },
  { slug: "columbia_math_major", label: "Mathematics" },
  { slug: "columbia_applied_math_major", label: "Applied Mathematics" },
  { slug: "columbia_cs_math", label: "Computer Science–Mathematics" },
  { slug: "columbia_math_stat", label: "Mathematics-Statistics" },
  { slug: "columbia_sustdev_major", label: "Sustainable Development" },
  { slug: "columbia_phil_major", label: "Philosophy" },
  { slug: "columbia_english_major", label: "English" },
];
const UNDERGRAD_MINORS = [
  { slug: "", label: "None" },
  { slug: "columbia_econ_concentration", label: "Economics (concentration)" },
  { slug: "columbia_cs_concentration", label: "Computer Science (concentration)" },
  { slug: "columbia_ai_minor", label: "Artificial Intelligence (minor)" },
  { slug: "columbia_math_concentration", label: "Mathematics (concentration)" },
  { slug: "columbia_math_minor", label: "Mathematics (minor)" },
  { slug: "columbia_math_prob_minor", label: "Mathematical Probability (minor)" },
  { slug: "columbia_sustdev_concentration", label: "Sustainable Development (concentration)" },
  { slug: "columbia_phil_concentration", label: "Philosophy (concentration)" },
  { slug: "columbia_english_concentration", label: "English (concentration)" },
];
const MAJOR_SLUGS = UNDERGRAD_MAJORS.map((m) => m.slug);
const MINOR_SLUGS = UNDERGRAD_MINORS.map((m) => m.slug).filter(Boolean);

function composePrograms(majorSlug: string, minorSlug: string): string[] {
  return ["columbia_cc_core", majorSlug, ...(minorSlug ? [minorSlug] : [])];
}

// MS pathway programs (cs.columbia.edu). "General" = no pathway chosen yet.
const MS_PATHWAYS: { slug: string; label: string }[] = [
  { slug: "columbia_ms_cs", label: "General (no pathway yet)" },
  { slug: "columbia_ms_cs_ml", label: "Machine Learning" },
  { slug: "columbia_ms_cs_nlp", label: "Natural Language Processing" },
  { slug: "columbia_ms_cs_security", label: "Computer Security" },
  { slug: "columbia_ms_cs_software", label: "Software Systems" },
  { slug: "columbia_ms_cs_networks", label: "Network Systems" },
  { slug: "columbia_ms_cs_compbio", label: "Computational Biology" },
  { slug: "columbia_ms_cs_foundations", label: "Foundations of Computer Science" },
  { slug: "columbia_ms_cs_vgir", label: "Vision, Graphics, Interaction & Robotics" },
  { slug: "columbia_ms_cs_personalized", label: "MS Personalized (faculty invite only)" },
  { slug: "columbia_ms_cs_thesis", label: "MS Thesis (faculty invite only)" },
];

const GRAD_PROGRAMS = [
  { slug: "columbia_ms_cs", label: "MS in Computer Science", major: "Computer Science (MS)" },
  { slug: "columbia_ma_philosophy", label: "MA in Philosophy", major: "Philosophy (MA)" },
];

export function degreeOf(programs: string[]): DegreeType {
  return programs.some((p) => p.startsWith("columbia_ms") || p.startsWith("columbia_ma_")) ? "ms" : "undergrad";
}

const DEFAULT: StudentCreate = {
  name: "",
  school: "Columbia University",
  major: "Computer Science",
  minor: "Economics",
  current_term: "Fall 2025",
  graduation_term: "Spring 2028",
  completed_courses: [],
  waived_courses: [],
  transfer_credits: [],
  preferred_workload: 3,
  max_credits_per_term: 17,
  career_goals: [],
  constraints: { no_summer: true, study_abroad_term: null },
  programs: [...UNDERGRAD_PROGRAMS, "columbia_econ_concentration"],
};

const CAREER_TAGS = [
  { id: "ai_ml", label: "AI / ML" },
  { id: "swe", label: "Software engineering" },
  { id: "systems", label: "Systems" },
  { id: "data", label: "Data" },
  { id: "quant", label: "Quant / Finance" },
  { id: "security", label: "Security" },
  { id: "research", label: "Research" },
  { id: "product", label: "Product" },
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const studentId = useSession((s) => s.studentId);
  const setStudentId = useSession((s) => s.setStudentId);
  const setPlans = useSession((s) => s.setPlans);
  const [searchParams] = useSearchParams();
  const isEdit = searchParams.get("edit") === "1" && !!studentId;

  const [step, setStep] = useState<Step>("Basics");
  const [form, setForm] = useState<StudentCreate>(DEFAULT);

  // Edit mode: prefill the form from the existing student instead of
  // silently creating a duplicate blank profile.
  const existingQ = useQuery({
    queryKey: ["student", studentId],
    enabled: isEdit,
    queryFn: () => api.getStudent(studentId!),
  });
  useEffect(() => {
    if (isEdit && existingQ.data) {
      const { id: _id, created_at: _c, ...rest } = existingQ.data;
      setForm({ ...rest, programs: rest.programs ?? DEFAULT.programs });
    }
  }, [isEdit, existingQ.data]);

  const create = useMutation({
    mutationFn: () =>
      isEdit ? api.updateStudent(studentId!, form) : api.createStudent(form),
    onSuccess: (student) => {
      setStudentId(student.id);
      // Profile changes invalidate previously generated plans.
      setPlans([]);
      queryClient.invalidateQueries();
      navigate("/dashboard");
    },
  });

  const { data: catalog } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.listCourses(),
  });

  const stepIdx = STEPS.indexOf(step);

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-6 py-12">
      <div className="mb-8 flex items-center gap-3">
        <Button variant="ghost" onClick={() => navigate("/")}>
          <ArrowLeft className="h-4 w-4" /> Back
        </Button>
        <div className="ml-auto text-xs text-muted">
          Step {stepIdx + 1} of {STEPS.length}
        </div>
      </div>

      <div className="mb-8 flex items-center gap-2">
        {STEPS.map((s, i) => (
          <div key={s} className="flex flex-1 items-center gap-2">
            <div
              className={cn(
                "grid h-7 w-7 place-items-center rounded-full border text-xs",
                i <= stepIdx
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-border text-muted",
              )}
            >
              {i < stepIdx ? <CheckCircle2 className="h-4 w-4" /> : i + 1}
            </div>
            <div
              className={cn(
                "text-xs",
                i === stepIdx ? "text-ink" : "text-muted",
              )}
            >
              {s}
            </div>
            {i < STEPS.length - 1 && (
              <div className="ml-auto h-px flex-1 bg-border" />
            )}
          </div>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{step}</CardTitle>
        </CardHeader>
        <CardBody>
          {step === "Basics" && <BasicsStep form={form} onChange={setForm} />}
          {step === "Completed" && (
            <CompletedStep form={form} onChange={setForm} catalog={catalog ?? []} />
          )}
          {step === "Workload" && <WorkloadStep form={form} onChange={setForm} />}
          {step === "Career" && <CareerStep form={form} onChange={setForm} />}
        </CardBody>
      </Card>

      <div className="mt-6 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => setStep(STEPS[Math.max(0, stepIdx - 1)])}
          disabled={stepIdx === 0}
        >
          <ArrowLeft className="h-4 w-4" /> Previous
        </Button>
        {stepIdx < STEPS.length - 1 ? (
          <Button variant="primary" onClick={() => setStep(STEPS[stepIdx + 1])}>
            Next <ArrowRight className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            variant="primary"
            onClick={() => create.mutate()}
            disabled={create.isPending}
          >
            {create.isPending
              ? "Saving…"
              : isEdit
                ? "Save changes"
                : "Finish & build my plan"}{" "}
            <ArrowRight className="h-4 w-4" />
          </Button>
        )}
      </div>

      {create.isError && (
        <div className="mt-4 rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          {(create.error as Error).message}
        </div>
      )}
    </div>
  );
}

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <div className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</div>
      {children}
      {hint && <div className="text-xs text-muted">{hint}</div>}
    </label>
  );
}

// Map a student's current standing → reasonable defaults for the planner.
// Assumes the user is about to start the next Fall term.
interface StandingPreset {
  id: string;
  label: string;
  description: string;
  current_term: string;
  graduation_term: string;
}

const UNDERGRAD_PRESETS: StandingPreset[] = [
  {
    id: "first_year",
    label: "Incoming first-year",
    description: "0 semesters complete · 8 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2030",
  },
  {
    id: "rising_sophomore",
    label: "Rising sophomore",
    description: "2 semesters complete · 6 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2029",
  },
  {
    id: "rising_junior",
    label: "Rising junior",
    description: "4 semesters complete · 4 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2028",
  },
  {
    id: "rising_senior",
    label: "Rising senior",
    description: "6 semesters complete · 2 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2027",
  },
];

const MS_PRESETS: StandingPreset[] = [
  {
    id: "ms_incoming",
    label: "Incoming grad student",
    description: "0 semesters complete · 4 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2028",
  },
  {
    id: "ms_second_year",
    label: "Second-year grad student",
    description: "2 semesters complete · 2 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2027",
  },
];

const START_TERM_OPTIONS = ["Fall 2025", "Spring 2026", "Fall 2026", "Spring 2027", "Fall 2027"];

function presetsFor(degree: DegreeType): StandingPreset[] {
  return degree === "ms" ? MS_PRESETS : UNDERGRAD_PRESETS;
}

function detectStanding(form: StudentCreate): string {
  const match = presetsFor(degreeOf(form.programs)).find(
    (s) => s.current_term === form.current_term && s.graduation_term === form.graduation_term,
  );
  return match?.id ?? "custom";
}

const DEGREE_OPTIONS: { id: DegreeType; label: string; description: string }[] = [
  {
    id: "undergrad",
    label: "Bachelor's (Columbia College)",
    description:
      "Core Curriculum + your major — CS, Economics (incl. joint majors), Math, " +
      "Data Science, Sustainable Development, Philosophy, English… pick below.",
  },
  {
    id: "ms",
    label: "Graduate (MS / MA)",
    description:
      "MS in Computer Science (10 pathways) or MA in Philosophy — pick your " +
      "program below.",
  },
];

function BasicsStep({
  form,
  onChange,
}: {
  form: StudentCreate;
  onChange: (f: StudentCreate) => void;
}) {
  const degree = degreeOf(form.programs);
  const presets = presetsFor(degree);
  const standing = detectStanding(form);

  const pickDegree = (id: DegreeType) => {
    if (id === degree) return;
    if (id === "ms") {
      const preset = MS_PRESETS[0];
      onChange({
        ...form,
        major: "Computer Science (MS)",
        minor: null,
        programs: [...MS_PROGRAMS],
        current_term: preset.current_term,
        graduation_term: preset.graduation_term,
        max_credits_per_term: Math.min(form.max_credits_per_term, 15),
      });
    } else {
      const preset = UNDERGRAD_PRESETS[0];
      onChange({
        ...form,
        major: "Computer Science",
        minor: "Economics",
        programs: [...UNDERGRAD_PROGRAMS, "columbia_econ_concentration"],
        current_term: preset.current_term,
        graduation_term: preset.graduation_term,
      });
    }
  };

  const pickStanding = (id: string) => {
    const preset = presets.find((s) => s.id === id);
    if (!preset) return;
    onChange({
      ...form,
      current_term: preset.current_term,
      graduation_term: preset.graduation_term,
    });
  };

  return (
    <div className="space-y-5">
      <Field label="Which degree are you planning?">
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {DEGREE_OPTIONS.map((d) => {
            const on = degree === d.id;
            return (
              <button
                key={d.id}
                type="button"
                onClick={() => pickDegree(d.id)}
                className={cn(
                  "rounded-xl border p-3 text-left transition",
                  on
                    ? "border-accent/60 bg-accent/10"
                    : "border-border bg-elevated hover:border-accent/40",
                )}
              >
                <div className="text-sm font-semibold">{d.label}</div>
                <div className="text-xs text-muted">{d.description}</div>
              </button>
            );
          })}
        </div>
      </Field>

      <Field
        label="Where are you in your degree?"
        hint="We'll prefill your starting and graduation terms. You can fine-tune them below."
      >
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {presets.map((s) => {
            const on = standing === s.id;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => pickStanding(s.id)}
                className={cn(
                  "rounded-xl border p-3 text-left transition",
                  on
                    ? "border-accent/60 bg-accent/10"
                    : "border-border bg-elevated hover:border-accent/40",
                )}
              >
                <div className="text-sm font-semibold">{s.label}</div>
                <div className="text-xs text-muted">{s.description}</div>
              </button>
            );
          })}
        </div>
        {standing === "custom" && (
          <div className="mt-2 text-xs text-muted">
            Using a custom term combination — edit the term selects below.
          </div>
        )}
      </Field>

      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Your name">
          <input
            className="input"
            value={form.name}
            onChange={(e) => onChange({ ...form, name: e.target.value })}
            placeholder="e.g. Amina A."
          />
        </Field>
        <Field label="School">
          <input className="input" value={form.school} disabled />
        </Field>
        {degree === "undergrad" ? (
          <Field label="Major">
            <select
              className="input"
              value={form.programs.find((p) => MAJOR_SLUGS.includes(p)) ?? "columbia_cs_major"}
              onChange={(e) => {
                const majorSlug = e.target.value;
                const minorSlug = form.programs.find((p) => MINOR_SLUGS.includes(p)) ?? "";
                const label = UNDERGRAD_MAJORS.find((m) => m.slug === majorSlug)!.label;
                onChange({
                  ...form,
                  major: label,
                  programs: composePrograms(majorSlug, minorSlug),
                });
              }}
            >
              {UNDERGRAD_MAJORS.map((m) => (
                <option key={m.slug} value={m.slug}>
                  {m.label}
                </option>
              ))}
            </select>
          </Field>
        ) : (
          <Field label="Graduate program">
            <select
              className="input"
              value={
                form.programs.some((p) => p.startsWith("columbia_ma_"))
                  ? "columbia_ma_philosophy"
                  : "columbia_ms_cs"
              }
              onChange={(e) => {
                const prog = GRAD_PROGRAMS.find((g) => g.slug === e.target.value)!;
                onChange({ ...form, major: prog.major, programs: [prog.slug] });
              }}
            >
              {GRAD_PROGRAMS.map((g) => (
                <option key={g.slug} value={g.slug}>
                  {g.label}
                </option>
              ))}
            </select>
          </Field>
        )}
        {degree === "ms" && form.programs.some((p) => p.startsWith("columbia_ms")) && (
          <Field
            label="MS pathway"
            hint="Each pathway has its own fundamental and secondary course requirements."
          >
            <select
              className="input"
              value={form.programs.find((p) => p.startsWith("columbia_ms")) ?? "columbia_ms_cs"}
              onChange={(e) => onChange({ ...form, programs: [e.target.value] })}
            >
              {MS_PATHWAYS.map((p) => (
                <option key={p.slug} value={p.slug}>
                  {p.label}
                </option>
              ))}
            </select>
          </Field>
        )}
        {degree === "undergrad" && (
          <Field label="Minor / concentration (optional)">
            <select
              className="input"
              value={form.programs.find((p) => MINOR_SLUGS.includes(p)) ?? ""}
              onChange={(e) => {
                const minorSlug = e.target.value;
                const majorSlug =
                  form.programs.find((p) => MAJOR_SLUGS.includes(p)) ?? "columbia_cs_major";
                const label = UNDERGRAD_MINORS.find((m) => m.slug === minorSlug)?.label;
                onChange({
                  ...form,
                  minor: minorSlug ? label ?? null : null,
                  programs: composePrograms(majorSlug, minorSlug),
                });
              }}
            >
              {UNDERGRAD_MINORS.map((m) => (
                <option key={m.slug} value={m.slug}>
                  {m.label}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Starting term" hint="When the plan begins.">
          <select
            className="input"
            value={form.current_term}
            onChange={(e) => {
              const start = e.target.value;
              // Graduation options depend on the start term — snap the
              // graduation pick when it falls outside the valid window.
              const valid = gradTermOptions(start, degree);
              const grad = valid.includes(form.graduation_term)
                ? form.graduation_term
                : defaultGradTerm(start, degree);
              onChange({ ...form, current_term: start, graduation_term: grad });
            }}
          >
            {START_TERM_OPTIONS.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Graduation term" hint="Must be after your starting term.">
          <select
            className="input"
            value={form.graduation_term}
            onChange={(e) => onChange({ ...form, graduation_term: e.target.value })}
          >
            {gradTermOptions(form.current_term, degree).map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </Field>
      </div>
    </div>
  );
}

function CompletedStep({
  form,
  onChange,
  catalog,
}: {
  form: StudentCreate;
  onChange: (f: StudentCreate) => void;
  catalog: { code: string; title: string; department: string }[];
}) {
  const [query, setQuery] = useState("");
  // MS students select courses taken during their bachelor's: those WAIVE
  // requirements but earn no credit toward the 30 points (department
  // policy), so they're stored separately from completed courses.
  const isMs = degreeOf(form.programs) === "ms";
  const fieldName = isMs ? ("waived_courses" as const) : ("completed_courses" as const);
  const currentList = form[fieldName] ?? [];
  const selected = new Set(currentList);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return catalog.filter(
      (c) =>
        !q ||
        c.code.toLowerCase().includes(q) ||
        c.title.toLowerCase().includes(q) ||
        c.department.toLowerCase().includes(q),
    );
  }, [catalog, query]);

  const toggle = (code: string) => {
    const next = new Set(selected);
    next.has(code) ? next.delete(code) : next.add(code);
    onChange({ ...form, [fieldName]: Array.from(next).sort() });
  };

  return (
    <div className="space-y-4">
      {isMs && (
        <div className="rounded-xl border border-border bg-elevated p-3 text-xs text-muted">
          Select courses you completed during your <span className="text-ink">bachelor's</span>.
          They waive the matching MS requirement, but they don't count toward your 30
          points — the plan will schedule replacement courses.
        </div>
      )}
      <input
        className="input"
        placeholder="Search by code, title, or department…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        {currentList.map((c) => (
          <Badge key={c} variant="accent" className="cursor-pointer" onClick={() => toggle(c)}>
            {c} ✕
          </Badge>
        ))}
      </div>
      <div className="grid max-h-72 grid-cols-1 gap-1 overflow-auto md:grid-cols-2">
        {filtered.slice(0, 80).map((c) => {
          const on = selected.has(c.code);
          return (
            <button
              key={c.code}
              onClick={() => toggle(c.code)}
              className={cn(
                "flex items-center justify-between rounded-xl border px-3 py-2 text-left text-sm transition",
                on
                  ? "border-accent/60 bg-accent/10"
                  : "border-border bg-elevated hover:border-accent/40",
              )}
            >
              <div>
                <div className="font-mono text-xs text-accent">{c.code}</div>
                <div className="text-xs text-ink">{c.title}</div>
              </div>
              {on && <CheckCircle2 className="h-4 w-4 text-ok" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function WorkloadStep({
  form,
  onChange,
}: {
  form: StudentCreate;
  onChange: (f: StudentCreate) => void;
}) {
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Field label="Preferred workload" hint="1 = light, 5 = brutal. Steers planner course selection.">
        <input
          type="range"
          min={1}
          max={5}
          value={form.preferred_workload}
          onChange={(e) =>
            onChange({ ...form, preferred_workload: parseInt(e.target.value, 10) })
          }
          className="w-full accent-cyan-400"
        />
        <div className="text-sm text-ink">Level {form.preferred_workload}</div>
      </Field>
      <Field label="Max credits per term">
        <input
          className="input"
          type="number"
          min={12}
          max={22}
          value={form.max_credits_per_term}
          onChange={(e) =>
            onChange({ ...form, max_credits_per_term: parseInt(e.target.value || "17", 10) })
          }
        />
      </Field>
      <div className="md:col-span-2 flex items-center gap-2">
        <input
          id="no_summer"
          type="checkbox"
          checked={Boolean((form.constraints as any).no_summer)}
          onChange={(e) =>
            onChange({
              ...form,
              constraints: { ...form.constraints, no_summer: e.target.checked },
            })
          }
        />
        <label htmlFor="no_summer" className="text-sm">
          Avoid summer terms in my plan
        </label>
      </div>
      {form.programs.some((p) => p.startsWith("columbia_ms")) && (
        <div className="md:col-span-2 flex items-center gap-2">
          <input
            id="include_research"
            type="checkbox"
            checked={Boolean((form.constraints as any).include_research)}
            onChange={(e) =>
              onChange({
                ...form,
                constraints: { ...form.constraints, include_research: e.target.checked },
              })
            }
          />
          <label htmlFor="include_research" className="text-sm">
            Include a research project (COMS E6901 — up to 3 of your 30 points; max 12
            research points overall)
          </label>
        </div>
      )}
    </div>
  );
}

function CareerStep({
  form,
  onChange,
}: {
  form: StudentCreate;
  onChange: (f: StudentCreate) => void;
}) {
  const selected = new Set(form.career_goals);
  const toggle = (id: string) => {
    const next = new Set(selected);
    next.has(id) ? next.delete(id) : next.add(id);
    onChange({ ...form, career_goals: Array.from(next) });
  };
  return (
    <div className="space-y-4">
      <div className="text-sm text-muted">
        Pick a few — the career-optimized plan will weight courses by your goals.
      </div>
      <div className="flex flex-wrap gap-2">
        {CAREER_TAGS.map((t) => {
          const on = selected.has(t.id);
          return (
            <button
              key={t.id}
              onClick={() => toggle(t.id)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm transition",
                on
                  ? "border-accent bg-accent/15 text-accent"
                  : "border-border bg-elevated text-muted hover:text-ink",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
