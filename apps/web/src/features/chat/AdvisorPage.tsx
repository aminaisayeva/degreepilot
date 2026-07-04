import { useMutation } from "@tanstack/react-query";
import {
  Bot,
  CheckCircle2,
  Eye,
  MessageSquare,
  RotateCcw,
  Send,
  ShieldCheck,
  User2,
  Wrench,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { api } from "@/lib/api";
import { cn, titleCase } from "@/lib/utils";
import { useSession } from "@/store/session";
import type {
  AdvisorResponse,
  AdvisorToolCall,
  AdvisorV2Response,
  AgentTrace,
  CriticViolation,
} from "@/types/api";

const SEEDS = [
  "Can I graduate on time?",
  "What requirements am I still missing?",
  "What if I study abroad junior spring?",
  "Which courses are best for AI/ML?",
  "Why did you recommend this plan?",
  "What's the risk in this plan?",
];

interface Msg {
  role: "user" | "assistant";
  content: string;
  intent?: string;
  tool_calls?: AdvisorToolCall[];
  suggestions?: string[];
  agent_trace?: AgentTrace[];
  retry_count?: number;
  critic_violations?: CriticViolation[];
}

export function AdvisorPage() {
  const studentId = useSession((s) => s.studentId);
  const plans = useSession((s) => s.plans);
  const activeIdx = useSession((s) => s.activePlanIndex);
  const plan = plans[activeIdx];

  const [useMultiAgent, setUseMultiAgent] = useState(true);
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "Hi — I'm your degree advisor. I answer using your audit, plan, and the planning engine — never invented courses. Try one of these:",
      suggestions: SEEDS,
    },
  ]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: async (message: string): Promise<AdvisorResponse | AdvisorV2Response> => {
      if (!studentId) throw new Error("No student selected.");
      return useMultiAgent
        ? api.chatV2(studentId, message, plan?.id ?? null)
        : api.chat(studentId, message, plan?.id ?? null);
    },
    onSuccess: (res) => {
      const v2 = "agent_trace" in res ? (res as AdvisorV2Response) : undefined;
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: res.answer,
          intent: res.intent,
          tool_calls: res.tool_calls,
          suggestions: res.suggestions,
          agent_trace: v2?.agent_trace,
          retry_count: v2?.retry_count,
          critic_violations: v2?.critic_violations,
        },
      ]);
    },
    onError: (e: Error) => {
      setMessages((m) => [...m, { role: "assistant", content: `Error: ${e.message}` }]);
    },
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, ask.isPending]);

  const send = (text: string) => {
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", content: text }]);
    setInput("");
    ask.mutate(text);
  };

  if (!studentId) {
    return (
      <Card>
        <CardBody className="text-center text-sm text-muted">
          Pick a student first.
        </CardBody>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 lg:grid-cols-12">
      <div className="lg:col-span-8 space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-2">
              <CardTitle>
                <span className="inline-flex items-center gap-2">
                  <MessageSquare className="h-4 w-4" /> Advisor
                </span>
              </CardTitle>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setUseMultiAgent((v) => !v)}
                  className={cn(
                    "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] transition",
                    useMultiAgent
                      ? "border-accent bg-accent/15 text-accent"
                      : "border-border bg-elevated text-muted hover:text-ink",
                  )}
                  title="Toggle multi-agent (v2) vs single-agent (v1) advisor"
                >
                  <ShieldCheck className="h-3 w-3" />
                  {useMultiAgent ? "Multi-agent v2" : "Single-agent v1"}
                </button>
                <Badge variant={plan ? "ok" : "warn"}>
                  {plan ? `Plan: ${plan.name}` : "No plan in context"}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardBody>
            <div
              ref={scrollRef}
              className="flex h-[520px] flex-col gap-3 overflow-y-auto pr-1"
            >
              {messages.map((m, i) => (
                <Bubble key={i} m={m} onSuggestion={(s) => send(s)} />
              ))}
              {ask.isPending && (
                <div className="self-start rounded-2xl bg-elevated px-3 py-2 text-sm text-muted">
                  thinking…
                </div>
              )}
            </div>
            <div className="mt-4 flex gap-2">
              <input
                className="input"
                placeholder="Ask anything about your plan or degree…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !ask.isPending && send(input)}
              />
              <Button
                variant="primary"
                onClick={() => send(input)}
                disabled={!input.trim() || ask.isPending}
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="lg:col-span-4 space-y-3">
        <Card>
          <CardHeader>
            <CardTitle>How this works</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3 text-sm">
            <p>
              Five agents work together: <span className="text-ink">Orchestrator</span> routes,{" "}
              <span className="text-ink">Researcher</span> gathers your audit,{" "}
              <span className="text-ink">Planner</span> proposes,{" "}
              <span className="text-ink">Critic</span> verifies (deterministic), and{" "}
              <span className="text-ink">Explainer</span> phrases the reply.
            </p>
            <p>
              The Critic runs Python, not an LLM — so the "no hallucinated course codes" rule
              is enforced by code. If it rejects, the Orchestrator retries up to 3 times before
              degrading honestly.
            </p>
            <div className="rounded-xl border border-border bg-elevated p-3 text-xs text-muted">
              Toggle the chip in the header to compare v1 (single-agent) vs v2 (multi-agent).
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Try a question</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2">
            {SEEDS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="block w-full rounded-xl border border-border bg-elevated px-3 py-2 text-left text-sm transition hover:border-accent/40"
              >
                {s}
              </button>
            ))}
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function Bubble({ m, onSuggestion }: { m: Msg; onSuggestion: (s: string) => void }) {
  const user = m.role === "user";
  return (
    <div className={cn("flex gap-2", user ? "self-end justify-end" : "self-start")}>
      {!user && (
        <div className="mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent/15 text-accent">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={cn("max-w-[80%] space-y-2", user && "text-right")}>
        <div
          className={cn(
            "inline-block rounded-2xl px-3 py-2 text-sm whitespace-pre-wrap",
            user
              ? "bg-accent text-accent-ink"
              : "border border-border bg-surface text-ink",
          )}
        >
          {m.content}
        </div>
        {m.intent && (
          <div className="text-[10px] uppercase tracking-wide text-muted">
            intent · {titleCase(m.intent)}
            {m.retry_count !== undefined && m.retry_count > 0 && (
              <span className="ml-2 text-warn">· {m.retry_count} retr{m.retry_count > 1 ? "ies" : "y"}</span>
            )}
          </div>
        )}

        {/* v2 agent trace panel */}
        {m.agent_trace && m.agent_trace.length > 0 && (
          <AgentTracePanel trace={m.agent_trace} violations={m.critic_violations ?? []} />
        )}

        {/* tool-call chips (v1 + v2) */}
        {m.tool_calls && m.tool_calls.length > 0 && (
          <div className="space-y-1">
            {m.tool_calls.map((tc, i) => (
              <div
                key={i}
                className="inline-flex max-w-full items-center gap-2 rounded-md border border-border bg-elevated px-2 py-1 text-[11px] text-muted"
              >
                <Wrench className="h-3 w-3" />
                <span className="font-mono">{tc.tool}</span>
                <span className="truncate opacity-70">
                  → {JSON.stringify(tc.output).slice(0, 120)}
                </span>
              </div>
            ))}
          </div>
        )}

        {m.suggestions && m.suggestions.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {m.suggestions.map((s) => (
              <button
                key={s}
                onClick={() => onSuggestion(s)}
                className="rounded-full border border-border bg-elevated px-3 py-1 text-xs text-muted transition hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
        )}
      </div>
      {user && (
        <div className="mt-1 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-elevated text-muted">
          <User2 className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

function AgentTracePanel({
  trace,
  violations,
}: {
  trace: AgentTrace[];
  violations: CriticViolation[];
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-xl border border-border bg-elevated/60">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl px-3 py-1.5 text-[11px] text-muted hover:bg-elevated"
      >
        <span className="inline-flex items-center gap-2">
          <Eye className="h-3 w-3" />
          Agent trace · {trace.length} step{trace.length === 1 ? "" : "s"}
        </span>
        <span>{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div className="space-y-1 border-t border-border px-3 py-2">
          {trace.map((t, i) => {
            const Icon =
              t.status === "rejected" ? XCircle :
              t.status === "retry" ? RotateCcw :
              CheckCircle2;
            const tone =
              t.status === "rejected" ? "text-danger" :
              t.status === "retry" ? "text-warn" :
              t.status === "error" ? "text-danger" :
              "text-ok";
            return (
              <div
                key={i}
                className="flex items-center gap-2 text-[11px]"
                title={`${t.action} · ${t.duration_ms}ms`}
              >
                <Icon className={cn("h-3 w-3 shrink-0", tone)} />
                <span className="w-20 shrink-0 font-mono text-muted">{t.agent}</span>
                <span className="w-12 shrink-0 text-right tabular-nums text-muted">
                  {t.duration_ms}ms
                </span>
                <span className="truncate text-ink">{t.summary}</span>
              </div>
            );
          })}
          {violations.length > 0 && (
            <div className="mt-2 space-y-1 border-t border-border pt-2">
              <div className="text-[10px] uppercase tracking-wide text-muted">
                Critic violations
              </div>
              {violations.map((v, i) => (
                <div
                  key={i}
                  className={cn(
                    "rounded-md border px-2 py-1 text-[11px]",
                    v.severity === "error"
                      ? "border-danger/40 bg-danger/10 text-danger"
                      : "border-warn/40 bg-warn/10 text-warn",
                  )}
                >
                  <span className="font-mono">{v.code}</span> · {v.message}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
