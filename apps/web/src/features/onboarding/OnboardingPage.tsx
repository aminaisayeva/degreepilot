import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { StudentCreate } from "@/types/api";

const STEPS = ["Basics", "Completed", "Workload", "Career"] as const;
type Step = (typeof STEPS)[number];

export type DegreeType = "undergrad" | "ms";

const UNDERGRAD_PROGRAMS = ["columbia_cc_core", "columbia_cs_major"];
const MS_PROGRAMS = ["columbia_ms_cs"];

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

export function degreeOf(programs: string[]): DegreeType {
  return programs.some((p) => p.startsWith("columbia_ms")) ? "ms" : "undergrad";
}

const DEFAULT: StudentCreate = {
  name: "",
  school: "Columbia University",
  major: "Computer Science",
  minor: "Economics",
  current_term: "Fall 2025",
  graduation_term: "Spring 2028",
  completed_courses: [],
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
    label: "Incoming MS student",
    description: "0 semesters complete · 4 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2028",
  },
  {
    id: "ms_second_year",
    label: "Second-year MS student",
    description: "2 semesters complete · 2 to go",
    current_term: "Fall 2026",
    graduation_term: "Spring 2027",
  },
];

const GRAD_TERM_OPTIONS: Record<DegreeType, string[]> = {
  undergrad: ["Spring 2027", "Fall 2027", "Spring 2028", "Spring 2029", "Spring 2030"],
  ms: ["Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028"],
};

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
    label: "Bachelor's — CS major",
    description: "Columbia College BA · Core + CS major (+ optional Econ minor)",
  },
  {
    id: "ms",
    label: "Master's — MS in CS",
    description: "SEAS graduate · 30 points, breadth + track depth",
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
        <Field label="Major">
          <input className="input" value={form.major} disabled />
        </Field>
        {degree === "ms" && (
          <Field
            label="Pathway"
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
          <Field label="Minor (optional)">
            <select
              className="input"
              value={form.minor ?? ""}
              onChange={(e) =>
                onChange({
                  ...form,
                  minor: e.target.value || null,
                  programs: e.target.value
                    ? [...UNDERGRAD_PROGRAMS, "columbia_econ_concentration"]
                    : [...UNDERGRAD_PROGRAMS],
                })
              }
            >
              <option value="">None</option>
              <option value="Economics">Economics</option>
            </select>
          </Field>
        )}
        <Field label="Starting term" hint="When the plan begins.">
          <select
            className="input"
            value={form.current_term}
            onChange={(e) => onChange({ ...form, current_term: e.target.value })}
          >
            {["Fall 2025", "Spring 2026", "Fall 2026", "Spring 2027"].map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </Field>
        <Field label="Graduation term">
          <select
            className="input"
            value={form.graduation_term}
            onChange={(e) => onChange({ ...form, graduation_term: e.target.value })}
          >
            {GRAD_TERM_OPTIONS[degree].map((t) => (
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
  const selected = new Set(form.completed_courses);
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
    onChange({ ...form, completed_courses: Array.from(next).sort() });
  };

  return (
    <div className="space-y-4">
      <input
        className="input"
        placeholder="Search by code, title, or department…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="flex flex-wrap gap-2">
        {form.completed_courses.map((c) => (
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
