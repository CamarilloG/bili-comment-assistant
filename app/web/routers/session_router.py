from __future__ import annotations

import asyncio
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class CreateSessionResponse(BaseModel):
    session_id: str


class RequestBody(BaseModel):
    request: str


class ConfirmBody(BaseModel):
    acceptance_criteria: Optional[Dict[str, Any]] = None


@router.post("/create", response_model=CreateSessionResponse)
async def create_session():
    from web.app import sessions, event_bus
    from ai_center.models.session import ExecutionSession

    session = ExecutionSession()
    sessions[session.session_id] = {
        "session": session,
        "plan": None,
        "report": None,
        "task": None,
    }
    return CreateSessionResponse(session_id=session.session_id)


@router.post("/{session_id}/request")
async def submit_request(session_id: str, body: RequestBody):
    from web.app import sessions, planner

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    if planner is None:
        raise HTTPException(503, "AI planner not initialized (check API key)")

    from web.app import model_router
    if not model_router.get_available_models():
        raise HTTPException(
            503,
            "AI 模型未配置。请在 config.yaml 中设置有效的 ai.api_key，然后重启服务。"
        )

    session = sdata["session"]
    session.original_request = body.request
    session.status = "planning"

    try:
        plan = await planner.plan(body.request)
        sdata["plan"] = plan
        session.status = "confirming"
        return {"status": "ok", "plan_id": plan.plan_id}
    except Exception as e:
        session.status = "failed"
        raise HTTPException(500, str(e))


@router.get("/{session_id}/plan")
async def get_plan(session_id: str):
    from web.app import sessions

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    plan = sdata.get("plan")
    if not plan:
        raise HTTPException(404, "No plan available yet")
    return plan.model_dump()


@router.post("/{session_id}/confirm")
async def confirm_plan(session_id: str, body: ConfirmBody = ConfirmBody()):
    from web.app import sessions

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    plan = sdata.get("plan")
    if not plan:
        raise HTTPException(400, "No plan to confirm")

    if body.acceptance_criteria:
        from ai_center.models.plan import AcceptanceCriteria, Checkpoint
        ac = body.acceptance_criteria
        plan.acceptance_criteria = AcceptanceCriteria(
            description=ac.get("description", plan.acceptance_criteria.description),
            checkpoints=[
                Checkpoint(**cp) for cp in ac.get("checkpoints", [])
            ] or plan.acceptance_criteria.checkpoints,
        )

    sdata["session"].status = "confirmed"
    return {"status": "confirmed"}


@router.post("/{session_id}/start")
async def start_execution(session_id: str):
    from web.app import sessions, executor

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    if executor is None:
        raise HTTPException(503, "Executor not initialized")
    plan = sdata.get("plan")
    if not plan:
        raise HTTPException(400, "No plan to execute")

    async def _run():
        try:
            report = await executor.execute_plan(plan, sdata["session"])
            sdata["report"] = report
        except Exception as e:
            from utils.logger import get_logger
            get_logger().error(f"Execution failed: {e}")
            sdata["session"].status = "failed"

    task = asyncio.create_task(_run())
    sdata["task"] = task
    sdata["session"].status = "running"
    return {"status": "started"}


@router.post("/{session_id}/stop")
async def stop_execution(session_id: str):
    from web.app import sessions, executor

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")

    task = sdata.get("task")
    if task and not task.done():
        task.cancel()

    session = sdata["session"]
    session.status = "stopped"
    return {"status": "stopped"}


@router.get("/{session_id}/status")
async def get_status(session_id: str):
    from web.app import sessions

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    session = sdata["session"]
    return session.get_summary()


@router.get("/{session_id}/report")
async def get_report(session_id: str):
    from web.app import sessions

    sdata = sessions.get(session_id)
    if not sdata:
        raise HTTPException(404, "Session not found")
    report = sdata.get("report")
    if not report:
        return {"status": sdata["session"].status, "message": "No report yet"}
    return report.to_dict()
