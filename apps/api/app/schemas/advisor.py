from pydantic import BaseModel, Field


class AdvisorRequest(BaseModel):
    student_id: int
    message: str
    plan_id: int | None = None  # optional plan to reason about


class AdvisorToolCall(BaseModel):
    tool: str
    inputs: dict = Field(default_factory=dict)
    output: dict = Field(default_factory=dict)


class AdvisorResponse(BaseModel):
    intent: str
    answer: str
    tool_calls: list[AdvisorToolCall] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AgentTrace(BaseModel):
    agent: str
    action: str
    status: str
    summary: str
    duration_ms: int = 0


class CriticViolationOut(BaseModel):
    code: str
    message: str
    severity: str


class AdvisorV2Response(AdvisorResponse):
    """v2 multi-agent response. Extends AdvisorResponse with trace + critic data."""

    agent_trace: list[AgentTrace] = Field(default_factory=list)
    retry_count: int = 0
    critic_violations: list[CriticViolationOut] = Field(default_factory=list)
