import { useQuery } from "@tanstack/react-query";
import { GitBranch } from "lucide-react";
import { useMemo, useState } from "react";
import ReactFlow, {
  Background,
  Controls,
  Edge,
  MarkerType,
  Node,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";

import { Badge } from "@/components/ui/Badge";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSession } from "@/store/session";
import type { Course } from "@/types/api";

export function GraphPage() {
  const studentId = useSession((s) => s.studentId);
  const plans = useSession((s) => s.plans);
  const activeIdx = useSession((s) => s.activePlanIndex);
  const plan = plans[activeIdx];

  const { data: courses } = useQuery({
    queryKey: ["courses"],
    queryFn: () => api.listCourses(),
  });
  const { data: student } = useQuery({
    queryKey: ["student", studentId],
    enabled: !!studentId,
    queryFn: () => api.getStudent(studentId!),
  });

  const catalog = useMemo(() => {
    const m = new Map<string, Course>();
    (courses ?? []).forEach((c) => m.set(c.code, c));
    return m;
  }, [courses]);

  const [mode, setMode] = useState<"plan" | "ai" | "all">("plan");

  const focusCodes = useMemo(() => {
    if (mode === "plan" && plan) {
      const planCodes = new Set<string>();
      plan.terms.forEach((t) => t.courses.forEach((c) => planCodes.add(c)));
      // include prereqs of plan courses
      planCodes.forEach((code) => {
        const c = catalog.get(code);
        c?.prerequisites.forEach((g) => g.forEach((p) => planCodes.add(p)));
      });
      return planCodes;
    }
    if (mode === "ai") {
      const set = new Set<string>();
      (courses ?? []).forEach((c) => {
        if (c.career_tags?.includes("ai_ml") || c.categories?.includes("cs_track_ai")) {
          set.add(c.code);
          c.prerequisites.forEach((g) => g.forEach((p) => set.add(p)));
        }
      });
      return set;
    }
    return new Set((courses ?? []).map((c) => c.code));
  }, [mode, plan, catalog, courses]);

  const completed = new Set(student?.completed_courses ?? []);

  const { nodes, edges } = useMemo(
    () => layoutGraph(focusCodes, catalog, completed),
    [focusCodes, catalog, completed],
  );

  return (
    <div className="space-y-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Prerequisite graph</h1>
          <p className="text-sm text-muted">
            Visualize how unlocking earlier courses opens later ones. Completed courses are
            highlighted.
          </p>
        </div>
        <div className="flex gap-2">
          <ModeChip on={mode === "plan"} onClick={() => setMode("plan")}>
            Current plan
          </ModeChip>
          <ModeChip on={mode === "ai"} onClick={() => setMode("ai")}>
            AI/ML track
          </ModeChip>
          <ModeChip on={mode === "all"} onClick={() => setMode("all")}>
            Everything
          </ModeChip>
        </div>
      </header>

      {mode === "plan" && !plan && (
        <div className="rounded-xl border border-warn/40 bg-warn/10 p-3 text-sm text-warn">
          No plan generated yet — showing the full catalog. Generate plans from the
          dashboard to focus this view on your schedule.
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              <span className="inline-flex items-center gap-2">
                <GitBranch className="h-4 w-4" /> {nodes.length} courses · {edges.length} prereq edges
              </span>
            </CardTitle>
            <div className="flex gap-2">
              <Badge variant="ok">Done</Badge>
              <Badge variant="accent">In plan</Badge>
              <Badge>Available</Badge>
            </div>
          </div>
        </CardHeader>
        <CardBody>
          <div style={{ height: 560 }} className="rounded-xl border border-border bg-surface">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              fitView
              proOptions={{ hideAttribution: true }}
              defaultEdgeOptions={{
                markerEnd: { type: MarkerType.ArrowClosed, color: "#64748b" },
              }}
            >
              <Background gap={20} color="#1f2937" />
              <Controls className="!bg-elevated !border-border" />
            </ReactFlow>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}

function ModeChip({
  on,
  onClick,
  children,
}: {
  on: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm transition",
        on
          ? "border-accent bg-accent/15 text-accent"
          : "border-border bg-elevated text-muted hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function layoutGraph(
  codes: Set<string>,
  catalog: Map<string, Course>,
  completed: Set<string>,
): { nodes: Node[]; edges: Edge[] } {
  // Compute depth per node within the focused subgraph
  const nodesArr = Array.from(codes).filter((c) => catalog.has(c));
  const depth = new Map<string, number>();
  function d(code: string, stack: Set<string>): number {
    if (depth.has(code)) return depth.get(code)!;
    if (stack.has(code)) return 0;
    stack.add(code);
    const course = catalog.get(code);
    if (!course || !course.prerequisites?.length) {
      depth.set(code, 0);
      stack.delete(code);
      return 0;
    }
    let best = 0;
    for (const g of course.prerequisites) {
      const gd = Math.min(
        ...g.map((p) => (codes.has(p) ? d(p, stack) : 0)),
      );
      best = Math.max(best, gd + 1);
    }
    depth.set(code, best);
    stack.delete(code);
    return best;
  }
  nodesArr.forEach((c) => d(c, new Set()));

  const cols = new Map<number, string[]>();
  nodesArr.forEach((c) => {
    const lvl = depth.get(c) ?? 0;
    cols.set(lvl, [...(cols.get(lvl) ?? []), c]);
  });
  // sort each column alphabetically for stability
  cols.forEach((arr) => arr.sort());

  const colWidth = 240;
  const rowHeight = 88;
  const nodes: Node[] = [];
  Array.from(cols.entries()).forEach(([lvl, arr]) => {
    arr.forEach((code, i) => {
      const course = catalog.get(code)!;
      const isCompleted = completed.has(code);
      nodes.push({
        id: code,
        position: { x: lvl * colWidth, y: i * rowHeight },
        data: {
          label: (
            <div className="px-3 py-2 text-left">
              <div className="font-mono text-[10px] opacity-80">{code}</div>
              <div className="text-[12px] leading-tight">{course.title}</div>
            </div>
          ),
        },
        style: {
          width: 200,
          background: isCompleted
            ? "rgba(16, 185, 129, 0.18)"
            : "hsl(220 18% 14%)",
          color: "hsl(220 20% 96%)",
          border: isCompleted
            ? "1px solid rgba(16, 185, 129, 0.55)"
            : "1px solid hsl(220 14% 22%)",
          borderRadius: 12,
          fontFamily: "Inter, sans-serif",
        },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      });
    });
  });

  const edges: Edge[] = [];
  const seenEdges = new Set<string>();
  nodesArr.forEach((code) => {
    const course = catalog.get(code)!;
    course.prerequisites?.forEach((g) =>
      g.forEach((pre) => {
        const id = `${pre}->${code}`;
        // a prereq can appear in multiple OR-groups — draw it once
        if (codes.has(pre) && !seenEdges.has(id)) {
          seenEdges.add(id);
          edges.push({
            id,
            source: pre,
            target: code,
            style: { stroke: "rgba(148, 163, 184, 0.45)" },
          });
        }
      }),
    );
  });
  return { nodes, edges };
}
