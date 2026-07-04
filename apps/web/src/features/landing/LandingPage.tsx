import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Brain,
  CalendarRange,
  CheckCircle2,
  GitMerge,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { useSession } from "@/store/session";

export function LandingPage() {
  const navigate = useNavigate();
  const setStudentId = useSession((s) => s.setStudentId);

  const { data: students } = useQuery({
    queryKey: ["students"],
    queryFn: () => api.listStudents(),
  });

  const useDemo = useMutation({
    mutationFn: async (name: string) => {
      const list = students ?? (await api.listStudents());
      const demo = list.find((s) => s.name === name) ?? list[0];
      if (!demo) throw new Error("No demo student is seeded yet — start the API.");
      return demo.id;
    },
    onSuccess: (id) => {
      setStudentId(id);
      navigate("/dashboard");
    },
  });

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-accent/15 text-accent">
            <CalendarRange className="h-4 w-4" />
          </div>
          <div className="text-base font-bold tracking-tight">DegreePilot</div>
          <Badge variant="default" className="ml-2">MVP · Columbia CS (BA + MS)</Badge>
        </div>
        <nav className="flex items-center gap-2">
          <Button variant="ghost" onClick={() => navigate("/courses")}>Browse catalog</Button>
          <Button variant="primary" onClick={() => navigate("/onboarding")}>
            Start onboarding <ArrowRight className="h-4 w-4" />
          </Button>
        </nav>
      </header>

      <section className="mx-auto max-w-6xl px-6 pt-12 pb-20">
        <div className="grid items-center gap-12 lg:grid-cols-12">
          <div className="lg:col-span-7">
            <Badge variant="accent" className="mb-6">
              <Sparkles className="h-3 w-3" /> Agentic academic planning
            </Badge>
            <h1 className="text-5xl font-extrabold tracking-tight md:text-6xl">
              Stop hoping your <span className="text-accent">degree plan</span> works.
              <br /> Generate one that does.
            </h1>
            <p className="mt-6 max-w-2xl text-lg text-muted">
              DegreePilot combines structured degree requirements, prerequisite graphs,
              workload scoring, and your career goals into a validated 4-year plan. The LLM
              explains. The planner validates.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button variant="primary" onClick={() => navigate("/onboarding")}>
                Build my plan <ArrowRight className="h-4 w-4" />
              </Button>
              <Button onClick={() => useDemo.mutate("Alex Demo")} disabled={useDemo.isPending}>
                {useDemo.isPending ? "Loading demo…" : "Try the undergrad demo"}
              </Button>
              <Button onClick={() => useDemo.mutate("Maya Demo")} disabled={useDemo.isPending}>
                Try the MS CS demo
              </Button>
            </div>

            <div className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-3">
              <FeaturePill icon={ShieldCheck} title="Deterministic" body="Prereqs, audit & validation in code — not LLM guesses." />
              <FeaturePill icon={Brain} title="Tool-using advisor" body="The chat calls planning APIs. No hallucinated courses." />
              <FeaturePill icon={GitMerge} title="Plan variants" body="Balanced, career-optimized, early-graduation side-by-side." />
            </div>
          </div>

          <div className="lg:col-span-5">
            <ProductCard />
          </div>
        </div>
      </section>

      <section className="mx-auto grid max-w-6xl gap-4 px-6 pb-20 md:grid-cols-3">
        <Step n={1} title="Tell us about your degree" body="School, major, completed courses, career goals, constraints." />
        <Step n={2} title="See your audit" body="Track every requirement, missing categories, and credit gaps." />
        <Step n={3} title="Plan & explore" body="Two AI-assisted plans, prereq graph, and a tool-using advisor." />
      </section>

      <footer className="mx-auto max-w-6xl px-6 pb-12 text-center text-xs text-muted">
        © DegreePilot demo — sample data, not affiliated with Columbia University.
      </footer>
    </div>
  );
}

function FeaturePill({
  icon: Icon,
  title,
  body,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  body: string;
}) {
  return (
    <div className="card card-pad">
      <Icon className="h-5 w-5 text-accent" />
      <div className="mt-3 text-sm font-semibold">{title}</div>
      <div className="mt-1 text-xs text-muted">{body}</div>
    </div>
  );
}

function Step({ n, title, body }: { n: number; title: string; body: string }) {
  return (
    <div className="card card-pad">
      <div className="text-xs font-semibold text-accent">STEP {n}</div>
      <div className="mt-2 text-base font-semibold">{title}</div>
      <div className="mt-2 text-sm text-muted">{body}</div>
    </div>
  );
}

function ProductCard() {
  return (
    <div className="card card-pad">
      <div className="text-xs font-semibold text-muted">FALL 2025 · BALANCED PLAN</div>
      <div className="mt-3 grid grid-cols-1 gap-2">
        {[
          { code: "MATH2010", title: "Linear Algebra", ok: true },
          { code: "STAT1201", title: "Stats (calc-based)", ok: true },
          { code: "COMS4231", title: "Algorithms", ok: true },
          { code: "COMS3261", title: "Theory of Computation", ok: true },
        ].map((c) => (
          <div key={c.code} className="flex items-center justify-between rounded-xl border border-border bg-elevated px-3 py-2">
            <div>
              <div className="font-mono text-xs text-accent">{c.code}</div>
              <div className="text-sm">{c.title}</div>
            </div>
            <CheckCircle2 className="h-4 w-4 text-ok" />
          </div>
        ))}
      </div>
      <div className="mt-4 flex items-center justify-between text-xs text-muted">
        <span>12 credits · workload 14</span>
        <Badge variant="ok">No conflicts</Badge>
      </div>
    </div>
  );
}
