import { useMutation, useQueries, useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  GraduationCap,
  Layers,
  Sparkles,
} from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Progress } from "@/components/ui/Progress";
import { Tabs } from "@/components/ui/Tabs";
import { api } from "@/lib/api";
import { formatPct, titleCase } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { AuditReport, Course, Requirement, RequirementProgress } from "@/types/api";

export function DashboardPage() {
  const navigate = useNavigate();
  const studentId = useSession((s) => s.studentId);
  const setStudentId = useSession((s) => s.setStudentId);
  const setPlans = useSession((s) => s.setPlans);

  const studentQ = useQuery({
    queryKey: ["student", studentId],
    enabled: !!studentId,
    queryFn: () => api.getStudent(studentId!),
    retry: (count, err) => !String(err).includes("404") && count < 2,
  });

  const programsQ = useQuery({
    queryKey: ["programs"],
    queryFn: () => api.listPrograms(),
  });

  // Only audit against the programs this student is actually pursuing.
  const studentPrograms = studentQ.data?.programs ?? [];
  const programs = (programsQ.data ?? []).filter(
    (p) => studentPrograms.length === 0 || studentPrograms.includes(p.slug),
  );

  const auditQueries = useQueries({
    queries: programs.map((p) => ({
      queryKey: ["audit", studentId, p.slug],
      enabled: !!studentId,
      queryFn: () => api.getAudit(studentId!, p.slug),
    })),
  });

  const [activeProgram, setActiveProgram] = useState<string | null>(null);

  const generate = useMutation({
    mutationFn: () =>
      api.generatePlans(studentId!, ["balanced", "career_optimized", "aggressive"]),
    onSuccess: (plans) => {
      setPlans(plans);
      navigate("/planner");
    },
  });

  const auditByProgram = useMemo(() => {
    const m = new Map<string, AuditReport>();
    programs.forEach((p, i) => {
      const data = auditQueries[i]?.data;
      if (data) m.set(p.slug, data);
    });
    return m;
  }, [programs, auditQueries]);

  if (!studentId) {
    return <NoStudent />;
  }
  if (studentQ.isLoading || programsQ.isLoading) {
    return <div className="text-muted">Loading audit…</div>;
  }
  if (studentQ.isError || programsQ.isError) {
    const stale = String(studentQ.error ?? "").includes("404");
    return (
      <Card>
        <CardBody className="text-center">
          <div className="text-base font-semibold text-danger">
            {stale
              ? "This student no longer exists (the database may have been reset)."
              : `Error: ${(studentQ.error || programsQ.error)?.toString()}`}
          </div>
          <div className="mt-4 flex justify-center gap-2">
            <Button
              variant="primary"
              onClick={() => {
                setStudentId(null);
                navigate("/");
              }}
            >
              Reset session
            </Button>
          </div>
        </CardBody>
      </Card>
    );
  }

  const student = studentQ.data!;
  const currentSlug = activeProgram ?? programs[0]?.slug;
  const currentAudit = currentSlug ? auditByProgram.get(currentSlug) : undefined;

  const { data: courseList } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.listCourses(),
  });
  const courseCatalog = useMemo(() => {
    const m = new Map<string, Course>();
    (courseList ?? []).forEach((c) => m.set(c.code, c));
    return m;
  }, [courseList]);

  const reqsQ = useQuery({
    queryKey: ["requirements", currentSlug],
    enabled: !!currentSlug,
    queryFn: () => api.getRequirements(currentSlug!),
  });
  const fullReqCourses = useMemo(() => {
    const m = new Map<number, string[]>();
    (reqsQ.data ?? []).forEach((r: Requirement) => m.set(r.id, r.courses));
    return m;
  }, [reqsQ.data]);

  const [noteCourse, setNoteCourse] = useState<string | null>(null);

  // Aggregated metrics across every program for the headline cards.
  // total_credits_completed is the student's global credit count (identical in
  // every audit) — take it once instead of summing per program.
  const allAudits = Array.from(auditByProgram.values());
  const sumCompleted = allAudits.reduce((a, b) => a + b.completed_count, 0);
  const sumTotal = allAudits.reduce((a, b) => a + b.total_count, 0);
  const sumCredits = allAudits[0]?.total_credits_completed ?? 0;
  const sumCreditsRequired = allAudits.reduce((a, b) => a + b.total_credits_required, 0);
  const overallWarn = allAudits.flatMap((a) => a.warnings);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs text-muted">{student.school}</div>
          <h1 className="text-2xl font-bold tracking-tight">
            {student.name || "Anonymous Student"}
          </h1>
          <div className="mt-1 flex flex-wrap gap-2 text-xs">
            <Badge>Major · {student.major}</Badge>
            {student.minor && <Badge>Minor · {student.minor}</Badge>}
            <Badge>Term · {student.current_term}</Badge>
            <Badge>Graduating · {student.graduation_term}</Badge>
          </div>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate("/onboarding?edit=1")}>Edit profile</Button>
          <Button
            variant="primary"
            onClick={() => generate.mutate()}
            disabled={generate.isPending}
          >
            <Sparkles className="h-4 w-4" />
            {generate.isPending ? "Generating…" : "Generate plans"}
          </Button>
        </div>
      </header>

      {generate.isError && (
        <div className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
          Plan generation failed: {(generate.error as Error).message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <Metric
          icon={Layers}
          label="Requirements complete"
          value={`${sumCompleted} / ${sumTotal}`}
          hint={sumTotal ? formatPct(sumCompleted / sumTotal) : "—"}
        />
        <Metric
          icon={GraduationCap}
          label="Credits completed"
          value={`${sumCredits.toFixed(0)}`}
          hint={`of ${sumCreditsRequired.toFixed(0)} requirement credits`}
        />
        <Metric
          icon={CalendarDays}
          label="Terms remaining"
          value={`${termsBetween(student.current_term, student.graduation_term)}`}
          hint={student.graduation_term}
        />
        <Metric
          icon={AlertTriangle}
          label="Warnings"
          value={`${overallWarn.length}`}
          hint={overallWarn.length ? "see below" : "all clear"}
        />
      </div>

      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <Tabs
            value={currentSlug ?? ""}
            onChange={(v) => setActiveProgram(v)}
            options={programs.map((p) => ({
              value: p.slug,
              label: (
                <span className="inline-flex items-center gap-2 px-1">
                  {p.label}
                  <ProgressDot audit={auditByProgram.get(p.slug)} />
                </span>
              ),
            }))}
          />
          <div className="ml-auto text-xs text-muted">
            Showing audit for{" "}
            <span className="text-ink">
              {programs.find((p) => p.slug === currentSlug)?.label}
            </span>
          </div>
        </div>

        {!currentAudit ? (
          <div className="text-sm text-muted">Loading audit…</div>
        ) : (
          <>
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>
                    Overall progress ·{" "}
                    {programs.find((p) => p.slug === currentSlug)?.label}
                  </CardTitle>
                  <span className="text-xs text-muted">
                    {formatPct(currentAudit.overall_progress_pct)}
                  </span>
                </div>
              </CardHeader>
              <CardBody>
                <Progress value={currentAudit.overall_progress_pct} />
                {(currentAudit.warnings.length > 0 || currentAudit.blockers.length > 0) && (
                  <div className="mt-4 space-y-2">
                    {currentAudit.warnings.map((w, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4" />
                        <div>{w}</div>
                      </div>
                    ))}
                    {currentAudit.blockers.map((b, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm text-danger"
                      >
                        <AlertTriangle className="mt-0.5 h-4 w-4" />
                        <div>{b}</div>
                      </div>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>

            <div>
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-muted">
                  Requirements · {titleCase(currentAudit.program)}
                </h2>
                <Button variant="ghost" onClick={() => navigate("/courses")}>
                  Browse catalog <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {currentAudit.requirements.map((r) => (
                  <RequirementCard
                    key={r.requirement_id}
                    r={r}
                    allOptions={fullReqCourses.get(r.requirement_id) ?? []}
                    onCourseClick={setNoteCourse}
                  />
                ))}
              </div>
            </div>
          </>
        )}
        {noteCourse && (
          <CourseNoteCard
            code={noteCourse}
            course={courseCatalog.get(noteCourse)}
            onClose={() => setNoteCourse(null)}
          />
        )}
      </div>
    </div>
  );
}

function ProgressDot({ audit }: { audit: AuditReport | undefined }) {
  if (!audit) return null;
  const pct = audit.overall_progress_pct;
  const tone = pct >= 1 ? "bg-ok" : pct >= 0.5 ? "bg-accent" : "bg-warn";
  return <span className={`inline-block h-1.5 w-1.5 rounded-full ${tone}`} />;
}

function termsBetween(start: string, end: string): number {
  // Inclusive Fall/Spring term count, e.g. Fall 2025 → Spring 2028 = 6.
  const idx = (t: string) => {
    const [season, year] = t.split(" ");
    const so = season === "Fall" ? 1 : season === "Summer" ? 0.5 : 0;
    return parseInt(year, 10) * 2 + so;
  };
  const span = idx(end) - idx(start);
  return Math.max(0, Math.floor(span) + 1);
}

function Metric({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="card card-pad">
      <div className="flex items-center gap-2 text-xs text-muted">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <div className="mt-2 text-3xl font-extrabold tracking-tight">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

function CourseChip({
  code,
  variant,
  onClick,
}: {
  code: string;
  variant?: "ok";
  onClick: (code: string) => void;
}) {
  return (
    <button onClick={() => onClick(code)} title="Course details" className="cursor-pointer">
      <Badge variant={variant} className="hover:ring-1 hover:ring-accent/60">
        {code}
      </Badge>
    </button>
  );
}

function CourseNoteCard({
  code,
  course,
  onClose,
}: {
  code: string;
  course: Course | undefined;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  return (
    <div
      className="fixed inset-0 z-50 grid place-items-center bg-black/50 p-4"
      onClick={onClose}
    >
      <div
        className="card card-pad w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="font-mono text-xs text-accent">{code}</div>
            <div className="text-lg font-semibold">{course?.title ?? "Not in catalog"}</div>
          </div>
          <button className="text-muted hover:text-ink" onClick={onClose}>✕</button>
        </div>
        {course ? (
          <div className="mt-3 space-y-2 text-sm">
            <div className="text-xs text-muted">
              {course.department} · {course.credits} credits ·{" "}
              {(course.offered_terms ?? []).join(", ") || "terms TBD"} · workload{" "}
              {course.workload_level}/5
            </div>
            {course.description && <p className="text-ink/90">{course.description}</p>}
            <div>
              <span className="text-[10px] uppercase tracking-wide text-muted">
                Prerequisites:{" "}
              </span>
              {course.prerequisites.length === 0
                ? "None"
                : course.prerequisites.map((g) => `(${g.join(" OR ")})`).join(" AND ")}
            </div>
            <Button variant="ghost" onClick={() => navigate("/courses")}>
              Open in catalog <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <p className="mt-3 text-sm text-muted">
            This code isn't in the current catalog — it may be a prefix variant or a
            course from an unscraped department.
          </p>
        )}
      </div>
    </div>
  );
}

function RequirementCard({
  r,
  allOptions,
  onCourseClick,
}: {
  r: RequirementProgress;
  allOptions: string[];
  onCourseClick: (code: string) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  return (
    <div className="card card-pad">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">{r.name}</div>
          <div className="mt-0.5 text-[11px] uppercase tracking-wide text-muted">
            {titleCase(r.type)}
          </div>
        </div>
        {r.satisfied ? (
          <Badge variant="ok">
            <CheckCircle2 className="h-3 w-3" /> Done
          </Badge>
        ) : (
          <Badge variant="warn">In progress</Badge>
        )}
      </div>

      <div className="mt-3">
        <Progress value={r.progress_pct} />
        <div className="mt-1 flex items-center justify-between text-xs text-muted">
          <span>{formatPct(r.progress_pct)}</span>
          <span>
            {r.earned_credits} / {(r.earned_credits + r.needed_credits).toFixed(1)} credits
          </span>
        </div>
      </div>

      {(r.completed_courses.length > 0 || r.missing_courses.length > 0) && (
        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {r.completed_courses.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-muted">Completed</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {r.completed_courses.map((c) => (
                  <CourseChip key={c} code={c} variant="ok" onClick={onCourseClick} />
                ))}
              </div>
            </div>
          )}
          {r.missing_courses.length > 0 && (
            <div>
              <div className="text-[10px] uppercase tracking-wide text-muted">Missing</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {r.missing_courses.slice(0, 6).map((c) => (
                  <CourseChip key={c} code={c} onClick={onCourseClick} />
                ))}
                {r.missing_courses.length > 6 && (
                  <Badge>+{r.missing_courses.length - 6}</Badge>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {allOptions.length > 0 && (
        <div className="mt-3">
          <button
            className="text-xs text-accent hover:underline"
            onClick={() => setShowAll(!showAll)}
          >
            {showAll ? "Hide options" : `Show all ${allOptions.length} option${allOptions.length === 1 ? "" : "s"}`}
          </button>
          {showAll && (
            <div className="mt-2 flex max-h-40 flex-wrap gap-1 overflow-y-auto">
              {allOptions.map((c) => (
                <CourseChip
                  key={c}
                  code={c}
                  variant={r.completed_courses.includes(c) ? "ok" : undefined}
                  onClick={onCourseClick}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {r.notes && <div className="mt-3 text-xs text-muted">{r.notes}</div>}
    </div>
  );
}

function NoStudent() {
  const navigate = useNavigate();
  return (
    <Card>
      <CardBody className="text-center">
        <div className="text-base font-semibold">No student selected.</div>
        <div className="mt-1 text-sm text-muted">
          Start onboarding or load the demo student to see an audit.
        </div>
        <div className="mt-4 flex justify-center gap-2">
          <Button variant="primary" onClick={() => navigate("/onboarding")}>
            Start onboarding
          </Button>
          <Button onClick={() => navigate("/")}>Use demo student</Button>
        </div>
      </CardBody>
    </Card>
  );
}
