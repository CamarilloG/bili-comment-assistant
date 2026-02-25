from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from modules.base import ActionResult


class TaskRecord(BaseModel):
    """Tracks the execution state and result of one task across rounds."""

    task_id: str
    status: str = "pending"  # pending, running, checking, accepted, failed, retrying, paused, terminated
    result: Optional[ActionResult] = None
    attempts: int = 0
    failure_reason: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class ExecutionSession(BaseModel):
    """Tracks the full lifecycle of one user request through multiple rounds."""

    session_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    plan_id: str = ""
    original_request: str = ""
    status: str = "created"  # created, planning, confirming, running, accepted, failed, stopped
    current_round: int = 0
    max_rounds: int = 10
    task_records: Dict[str, TaskRecord] = Field(default_factory=dict)
    round_history: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None

    def init_from_plan(self, plan_id: str, task_ids: List[str]) -> None:
        self.plan_id = plan_id
        for tid in task_ids:
            self.task_records[tid] = TaskRecord(task_id=tid)

    def mark_task_running(self, task_id: str) -> None:
        rec = self.task_records[task_id]
        rec.status = "running"
        rec.attempts += 1
        rec.started_at = datetime.now()

    def mark_task_completed(self, task_id: str, result: ActionResult) -> None:
        rec = self.task_records[task_id]
        rec.status = "checking"
        rec.result = result
        rec.finished_at = datetime.now()

    def mark_task_accepted(self, task_id: str) -> None:
        self.task_records[task_id].status = "accepted"

    def mark_task_failed(self, task_id: str, reason: str) -> None:
        rec = self.task_records[task_id]
        rec.status = "failed"
        rec.failure_reason = reason
        rec.finished_at = datetime.now()

    def mark_task_needs_retry(self, task_id: str, reason: str) -> None:
        rec = self.task_records[task_id]
        rec.status = "retrying"
        rec.failure_reason = reason

    def mark_task_paused(self, task_id: str) -> None:
        self.task_records[task_id].status = "paused"

    def mark_task_terminated(self, task_id: str) -> None:
        self.task_records[task_id].status = "terminated"

    def get_summary(self) -> Dict[str, Any]:
        statuses = [r.status for r in self.task_records.values()]
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_round": self.current_round,
            "total_tasks": len(self.task_records),
            "accepted": statuses.count("accepted"),
            "failed": statuses.count("failed"),
            "running": statuses.count("running"),
            "pending": statuses.count("pending"),
            "retrying": statuses.count("retrying"),
            "task_details": {
                tid: {
                    "status": rec.status,
                    "attempts": rec.attempts,
                    "failure_reason": rec.failure_reason,
                }
                for tid, rec in self.task_records.items()
            },
        }

    def all_accepted(self) -> bool:
        return all(r.status == "accepted" for r in self.task_records.values())

    def has_failed_tasks(self) -> bool:
        return any(r.status == "failed" for r in self.task_records.values())

    def retryable_task_ids(self, max_retries: int = 3) -> List[str]:
        return [
            tid
            for tid, rec in self.task_records.items()
            if rec.status in ("failed", "retrying") and rec.attempts < max_retries
        ]
