from __future__ import annotations

import json
from typing import Any, Dict, Optional

from utils.logger import get_logger
from ai_center.planner import Planner
from ai_center.dispatcher import Dispatcher
from ai_center.validator import Validator
from ai_center.event_bus import EventBus
from ai_center.state_machine import TaskStateMachine
from ai_center.models.plan import ExecutionPlan
from ai_center.models.session import ExecutionSession
from ai_center.models.events import EventType

logger = get_logger()


class ExecutionReport:
    """Final report produced by the Executor."""

    def __init__(self, session: ExecutionSession, plan: ExecutionPlan) -> None:
        self.session = session
        self.plan = plan

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session.session_id,
            "status": self.session.status,
            "rounds": self.session.current_round,
            "summary": self.session.get_summary(),
            "original_request": self.plan.original_request,
        }


class Executor:
    """Multi-round execution engine.

    Each round: dispatch tasks -> validate sub-tasks -> overall validation.
    If overall validation fails and rounds remain, the Planner adjusts the
    plan and a new round starts.
    """

    MAX_ROUNDS = 10

    def __init__(
        self,
        planner: Planner,
        dispatcher: Dispatcher,
        validator: Validator,
        event_bus: Optional[EventBus] = None,
        state_machine: Optional[TaskStateMachine] = None,
    ) -> None:
        self.planner = planner
        self.dispatcher = dispatcher
        self.validator = validator
        self.event_bus = event_bus or EventBus()
        self.fsm = state_machine or TaskStateMachine(self.event_bus)

    async def execute_plan(
        self, plan: ExecutionPlan, session: ExecutionSession | None = None
    ) -> ExecutionReport:
        if session is None:
            session = ExecutionSession(
                plan_id=plan.plan_id,
                original_request=plan.original_request,
                status="running",
            )
        else:
            session.plan_id = plan.plan_id
            session.original_request = plan.original_request
            session.status = "running"
        session.init_from_plan(
            plan.plan_id, [t.task_id for t in plan.tasks]
        )

        for task in plan.tasks:
            self.fsm.register(task.task_id, "pending")

        for round_num in range(1, self.MAX_ROUNDS + 1):
            session.current_round = round_num
            await self.event_bus.emit_simple(
                EventType.ROUND_START,
                session_id=session.session_id,
                data={"round": round_num},
                message=f"=== Round {round_num} ===",
            )

            async for event in self.dispatcher.dispatch(plan, session.session_id):
                task_id = event.task_id
                result_data = event.data.get("result", {})

                # Skip tasks that are already in a terminal state
                if self.fsm.is_terminal(task_id):
                    continue

                if event.event_type == EventType.TASK_COMPLETED:
                    from modules.base import ActionResult
                    ar = ActionResult(**result_data) if isinstance(result_data, dict) else ActionResult(success=False)

                    cur = self.fsm.get_state(task_id)
                    if cur == "pending":
                        await self.fsm.transition(task_id, "running", session.session_id)
                    session.mark_task_completed(task_id, ar)
                    await self.fsm.transition(task_id, "checking", session.session_id)

                    task = plan.get_task(task_id)
                    sub_check = await self.validator.check_task(task, ar)
                    if sub_check.passed:
                        session.mark_task_accepted(task_id)
                        await self.fsm.transition(task_id, "accepted", session.session_id)
                    else:
                        reason = "; ".join(sub_check.failures)
                        session.mark_task_needs_retry(task_id, reason)
                        await self.fsm.transition(task_id, "retrying", session.session_id, reason)

                elif event.event_type == EventType.TASK_FAILED:
                    error = result_data.get("error", event.data.get("error", "unknown"))
                    cur = self.fsm.get_state(task_id)
                    if cur == "pending":
                        await self.fsm.transition(task_id, "running", session.session_id)
                    session.mark_task_failed(task_id, str(error))
                    try:
                        await self.fsm.transition(task_id, "failed", session.session_id, str(error))
                    except Exception:
                        pass

            # If all tasks already accepted, skip AI validation
            if session.all_accepted():
                session.status = "accepted"
                break

            # Overall validation
            await self.event_bus.emit_simple(
                EventType.VALIDATION_START,
                session_id=session.session_id,
                data={"round": round_num},
            )

            overall = await self.validator.check_overall(
                plan.acceptance_criteria, session
            )

            await self.event_bus.emit_simple(
                EventType.VALIDATION_RESULT,
                session_id=session.session_id,
                data={
                    "passed": overall.passed,
                    "failures": overall.failures,
                    "summary": overall.summary,
                },
            )

            if overall.passed:
                session.status = "accepted"
                break

            # Adjust plan for next round
            summary = session.get_summary()
            plan = await self.planner.adjust_plan(plan, summary, overall.failures)

            await self.event_bus.emit_simple(
                EventType.ROUND_END,
                session_id=session.session_id,
                data={"round": round_num, "status": "retry", "reason": overall.summary},
                message=f"Round {round_num} failed, adjusting plan",
            )

            # Reset retryable tasks for the next round
            for tid in session.retryable_task_ids():
                session.task_records[tid].status = "pending"
                self.fsm.register(tid, "pending")
        else:
            session.status = "failed"

        # Final report
        report = ExecutionReport(session, plan)
        await self.event_bus.emit_simple(
            EventType.FINAL_REPORT,
            session_id=session.session_id,
            data=report.to_dict(),
            message=f"Execution finished: {session.status}",
        )
        return report

    async def stop(self, session: ExecutionSession) -> None:
        session.status = "stopped"
        logger.info(f"Session {session.session_id} stopped by user")
