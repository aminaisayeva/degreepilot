from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.models.course import Course
from app.models.plan import Plan
from app.models.requirement import Requirement
from app.models.student import Student
from app.schemas.advisor import (
    AdvisorRequest,
    AdvisorResponse,
    AdvisorV2Response,
    AgentTrace,
    CriticViolationOut,
)
from app.schemas.plan import PlanRead, SemesterPlan
from app.services.ai.advisor import answer_advisor
from app.services.ai.agents.orchestrator import Orchestrator

router = APIRouter()


def _plan_to_read(p: Plan) -> PlanRead:
    return PlanRead(
        id=p.id,
        student_id=p.student_id,
        name=p.name,
        strategy=p.strategy,
        terms=[SemesterPlan(**t) for t in p.terms],
        warnings=p.warnings,
        summary=p.summary,
        created_at=p.created_at,
    )


def _student_reqs(session: Session, student: Student) -> list[Requirement]:
    return list(
        session.exec(
            select(Requirement)
            .where(Requirement.program.in_(student.resolve_programs()))  # type: ignore[attr-defined]
            .order_by(Requirement.display_order)
        ).all()
    )


@router.post("/chat", response_model=AdvisorResponse)
def chat(payload: AdvisorRequest, session: Session = Depends(get_session)) -> AdvisorResponse:
    student = session.get(Student, payload.student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    catalog = {c.code: c for c in session.exec(select(Course)).all()}
    reqs = _student_reqs(session, student)
    plan_read = None
    if payload.plan_id is not None:
        p = session.get(Plan, payload.plan_id)
        if p:
            plan_read = _plan_to_read(p)
    return answer_advisor(payload, student, catalog, reqs, plan_read)


@router.post("/v2/chat", response_model=AdvisorV2Response)
def chat_v2(payload: AdvisorRequest, session: Session = Depends(get_session)) -> AdvisorV2Response:
    """Multi-agent advisor — Researcher → Planner → Critic → Explainer with retries."""
    student = session.get(Student, payload.student_id)
    if not student:
        raise HTTPException(404, "Student not found")
    catalog = {c.code: c for c in session.exec(select(Course)).all()}
    reqs = _student_reqs(session, student)
    plan_read = None
    if payload.plan_id is not None:
        p = session.get(Plan, payload.plan_id)
        if p:
            plan_read = _plan_to_read(p)

    orch = Orchestrator(student, catalog, reqs, plan=plan_read)
    scratchpad = orch.run(
        user_message=payload.message,
        student_id=payload.student_id,
        plan_id=payload.plan_id,
    )
    final = scratchpad.final_response or {}
    violations = scratchpad.critic_verdict.violations if scratchpad.critic_verdict else []
    return AdvisorV2Response(
        intent=final.get("intent", scratchpad.intent or "general"),
        answer=final.get("answer", ""),
        tool_calls=[
            {"tool": tc.tool, "inputs": tc.inputs, "output": tc.output}
            for tc in scratchpad.tool_calls
        ],
        citations=final.get("citations", []),
        suggestions=final.get("suggestions", []),
        agent_trace=[AgentTrace(**t) for t in scratchpad.trace_dict()],
        retry_count=scratchpad.retry_count,
        critic_violations=[
            CriticViolationOut(code=v.code, message=v.message, severity=v.severity)
            for v in violations
        ],
    )
