import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Crown, Workflow } from "lucide-react";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Progress } from "@/components/ui/Progress";
import { api } from "@/lib/api";
import { cn, formatPct } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { Plan } from "@/types/api";

export function ComparePage() {
  const navigate = useNavigate();
  const studentId = useSession((s) => s.studentId);
  const plans = useSession((s) => s.plans);

  // Key on plan ids + content so regenerating (same names, new courses)
  // invalidates the cached comparison.
  const plansKey = plans
    .map((p) => `${p.id ?? p.name}:${p.summary?.total_credits}:${p.terms.length}`)
    .join("|");
  const compareQ = useQuery({
    queryKey: ["compare", studentId, plansKey],
    enabled: !!studentId && plans.length >= 2,
    queryFn: () => api.comparePlans(studentId!, plans),
  });

  const winner = compareQ.data?.winner;

  if (!studentId) return <Empty title="Pick a student first." />;
  if (plans.length < 2)
    return (
      <Empty
        title="Generate plans first."
        body="Comparison needs at least two plan variants."
        onAction={() => navigate("/planner")}
        actionLabel="Open planner"
      />
    );

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Plan comparison</h1>
          <p className="text-sm text-muted">
            Side-by-side comparison of every generated variant. The winner is chosen on
            feasibility → completeness → career alignment → workload variance → length.
          </p>
        </div>
        {compareQ.data && winner && (
          <Badge variant="accent" className="text-sm">
            <Crown className="h-4 w-4" /> Winner · {winner}
          </Badge>
        )}
      </header>

      {compareQ.data?.rationale && (
        <Card>
          <CardBody className="text-sm">{compareQ.data.rationale}</CardBody>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {plans.map((p) => (
          <PlanCompareCard key={p.name} plan={p} isWinner={p.name === winner} />
        ))}
      </div>
    </div>
  );
}

function PlanCompareCard({ plan, isWinner }: { plan: Plan; isWinner: boolean }) {
  const errs = plan.warnings.filter((w) => w.severity === "error").length;
  const warns = plan.warnings.filter((w) => w.severity === "warning").length;
  const completion = (plan.summary?.post_plan_completion_pct as number) ?? 0;
  const career = (plan.summary?.career_alignment as number) ?? 0;
  const variance = (plan.summary?.workload_variance as number) ?? 0;
  return (
    <Card className={cn(isWinner && "ring-1 ring-accent/60 shadow-glow")}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <span className="inline-flex items-center gap-2">
              <Workflow className="h-4 w-4" /> {plan.name}
            </span>
          </CardTitle>
          {isWinner && (
            <Badge variant="accent">
              <Crown className="h-3 w-3" /> Winner
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardBody className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <Stat label="Strategy" value={plan.strategy} />
          <Stat label="Terms" value={plan.terms.length} />
          <Stat label="Career align" value={formatPct(career)} accent />
          <Stat label="Workload var" value={variance.toFixed(2)} />
          <Stat
            label="Blockers"
            value={errs}
            tone={errs ? "danger" : "ok"}
          />
          <Stat label="Warnings" value={warns} tone={warns ? "warn" : "ok"} />
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between text-xs text-muted">
            <span>Coverage</span>
            <span>{formatPct(completion)}</span>
          </div>
          <Progress value={completion} />
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted">Term skeleton</div>
          <div className="mt-1 space-y-1 text-xs">
            {plan.terms.map((t) => (
              <div key={t.term} className="flex items-center justify-between rounded-md bg-elevated px-2 py-1">
                <span className="text-ink">{t.term}</span>
                <span className="text-muted">{t.total_credits} cr · load {t.workload_score}</span>
              </div>
            ))}
          </div>
        </div>
        {errs === 0 && warns === 0 && (
          <div className="flex items-center gap-2 text-xs text-ok">
            <CheckCircle2 className="h-3 w-3" /> No structural issues
          </div>
        )}
      </CardBody>
    </Card>
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
  const cls =
    tone === "ok" ? "text-ok" :
    tone === "warn" ? "text-warn" :
    tone === "danger" ? "text-danger" :
    accent ? "text-accent" : "";
  return (
    <div className="rounded-lg bg-elevated px-2 py-2">
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className={cn("text-sm font-semibold", cls)}>{value as any}</div>
    </div>
  );
}

function Empty({
  title,
  body,
  onAction,
  actionLabel,
}: {
  title: string;
  body?: string;
  onAction?: () => void;
  actionLabel?: string;
}) {
  return (
    <Card>
      <CardBody className="text-center">
        <div className="text-base font-semibold">{title}</div>
        {body && <div className="mt-1 text-sm text-muted">{body}</div>}
        {onAction && actionLabel && (
          <Button variant="primary" className="mt-3" onClick={onAction}>
            {actionLabel}
          </Button>
        )}
      </CardBody>
    </Card>
  );
}
