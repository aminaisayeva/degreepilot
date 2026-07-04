"""Shared scratchpad passed between agents.

Each agent reads upstream fields and writes only to its own. The scratchpad
is the single piece of state in the multi-agent advisor — no implicit
globals, no hidden context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentTraceEntry:
    """One row in the agent_trace shown to the user."""

    agent: str                  # "Researcher" | "Planner" | "Critic" | "Explainer"
    action: str                 # short human label
    status: str                 # "ok" | "retry" | "rejected" | "error"
    summary: str                # short text rendered next to the chip
    duration_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "action": self.action,
            "status": self.status,
            "summary": self.summary,
            "duration_ms": self.duration_ms,
        }


@dataclass
class CriticViolation:
    code: str       # "hallucinated_code" | "ungrounded_grad_claim" | "plan_error" | "missing_citation"
    message: str
    severity: str   # "error" | "warning"

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class CriticVerdict:
    ok: bool
    violations: list[CriticViolation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "violations": [v.to_dict() for v in self.violations]}


@dataclass
class ToolCallRecord:
    """One tool invocation done by any agent."""

    tool: str
    inputs: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"tool": self.tool, "inputs": self.inputs, "output": self.output}


@dataclass
class AdvisorScratchpad:
    """The single piece of state passed between agents.

    Each agent reads upstream fields and writes only to its own.
    """

    # Inputs
    user_message: str
    student_id: int
    plan_id: int | None = None

    # Orchestrator writes
    intent: str | None = None
    retry_count: int = 0
    final_response: dict | None = None

    # Researcher writes
    context: dict[str, Any] = field(default_factory=dict)

    # Planner writes
    candidate_plan: dict | None = None
    candidate_answer: str | None = None

    # Critic writes
    critic_verdict: CriticVerdict | None = None

    # Anyone can append
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    agent_trace: list[AgentTraceEntry] = field(default_factory=list)

    def add_trace(
        self,
        agent: str,
        action: str,
        status: str,
        summary: str,
        duration_ms: int = 0,
    ) -> None:
        self.agent_trace.append(
            AgentTraceEntry(
                agent=agent,
                action=action,
                status=status,
                summary=summary,
                duration_ms=duration_ms,
            )
        )

    def add_tool_call(self, tool: str, inputs: dict, output: dict) -> None:
        self.tool_calls.append(ToolCallRecord(tool=tool, inputs=inputs, output=output))

    def trace_dict(self) -> list[dict]:
        return [t.to_dict() for t in self.agent_trace]

    def tool_calls_dict(self) -> list[dict]:
        return [t.to_dict() for t in self.tool_calls]
