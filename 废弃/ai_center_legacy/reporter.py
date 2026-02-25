from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from ai_center.models.session import ExecutionSession
from ai_center.models.plan import ExecutionPlan


class Reporter:
    """Generates structured delivery reports from execution sessions."""

    async def generate(
        self,
        session: ExecutionSession,
        plan: Optional[ExecutionPlan] = None,
    ) -> Dict[str, Any]:
        summary = session.get_summary()
        report = {
            "report_id": f"rpt_{session.session_id}",
            "generated_at": datetime.now().isoformat(),
            "session_id": session.session_id,
            "original_request": session.original_request,
            "status": session.status,
            "rounds_executed": session.current_round,
            "summary": {
                "total_tasks": summary["total_tasks"],
                "accepted": summary["accepted"],
                "failed": summary["failed"],
            },
            "task_details": [],
            "round_history": session.round_history,
        }

        for tid, rec in session.task_records.items():
            detail: Dict[str, Any] = {
                "task_id": tid,
                "status": rec.status,
                "attempts": rec.attempts,
            }
            if rec.result:
                detail["result_data"] = rec.result.data
            if rec.failure_reason:
                detail["failure_reason"] = rec.failure_reason
            report["task_details"].append(detail)

        return report

    async def export_json(
        self, session: ExecutionSession, plan: Optional[ExecutionPlan] = None
    ) -> str:
        report = await self.generate(session, plan)
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    async def export_csv(
        self, session: ExecutionSession, plan: Optional[ExecutionPlan] = None
    ) -> str:
        report = await self.generate(session, plan)
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["TaskID", "Status", "Attempts", "FailureReason"])
        for detail in report["task_details"]:
            writer.writerow([
                detail["task_id"],
                detail["status"],
                detail["attempts"],
                detail.get("failure_reason", ""),
            ])
        return buf.getvalue()
