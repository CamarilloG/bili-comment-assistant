from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from utils.logger import get_logger
from modules.registry import ModuleRegistry
from ai_center.model_router import ModelRouter
from ai_center.models.plan import (
    AcceptanceCriteria,
    Checkpoint,
    ExecutionPlan,
    RetryPolicy,
    TaskNode,
)
from ai_center.prompts.planner_prompts import (
    PLANNER_SYSTEM_PROMPT,
    PLANNER_USER_PROMPT,
    PLAN_ADJUSTMENT_SYSTEM,
    PLAN_ADJUSTMENT_USER,
)

logger = get_logger()


class Planner:
    """Decomposes a user request into a structured ExecutionPlan using AI."""

    def __init__(
        self,
        module_registry: ModuleRegistry,
        model_router: ModelRouter,
    ) -> None:
        self.registry = module_registry
        self.router = model_router

    async def plan(self, user_request: str) -> ExecutionPlan:
        capabilities = self.registry.get_all_capabilities()
        caps_json = json.dumps(
            [c.model_dump() for c in capabilities], ensure_ascii=False, indent=2
        )

        system_prompt = PLANNER_SYSTEM_PROMPT.format(capabilities_json=caps_json)
        user_prompt = PLANNER_USER_PROMPT.format(user_request=user_request)

        raw = await self.router.call(
            task_type="planning",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=2048,
            temperature=0.3,
        )

        if not raw:
            raise RuntimeError("Planner: AI returned empty response")

        plan = self._parse_plan(raw, user_request)

        feasibility = await self._validate_feasibility(plan)
        if feasibility:
            logger.warning(f"Planner feasibility issues: {feasibility}")

        return plan

    async def adjust_plan(
        self,
        plan: ExecutionPlan,
        session_summary: Dict[str, Any],
        failures: list[str],
    ) -> ExecutionPlan:
        system_prompt = PLAN_ADJUSTMENT_SYSTEM.format(
            current_plan_json=plan.model_dump_json(indent=2),
            execution_summary_json=json.dumps(session_summary, ensure_ascii=False, indent=2),
            failure_reasons="\n".join(f"- {f}" for f in failures),
        )

        raw = await self.router.call(
            task_type="planning",
            system_prompt=system_prompt,
            user_prompt=PLAN_ADJUSTMENT_USER,
            max_tokens=2048,
            temperature=0.3,
        )

        if not raw:
            logger.warning("Plan adjustment returned empty, keeping original plan")
            return plan

        try:
            return self._parse_plan(raw, plan.original_request)
        except Exception as e:
            logger.error(f"Failed to parse adjusted plan: {e}, keeping original")
            return plan

    def _parse_plan(self, raw: str, original_request: str) -> ExecutionPlan:
        cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Planner output is not valid JSON: {e}\nRaw: {raw[:500]}")

        if "error" in data:
            raise ValueError(f"Planner refused: {data['error']}")

        tasks = []
        dag: Dict[str, list[str]] = {}
        for t in data.get("tasks", []):
            ac_data = t.get("acceptance", {})
            checkpoints = [Checkpoint(**cp) for cp in ac_data.get("checkpoints", [])]
            node = TaskNode(
                task_id=t.get("task_id", ""),
                description=t.get("description", ""),
                module_id=t.get("module_id", ""),
                action=t.get("action", ""),
                params=t.get("params", {}),
                depends_on=t.get("depends_on", []),
                acceptance=AcceptanceCriteria(
                    description=ac_data.get("description", ""),
                    checkpoints=checkpoints,
                ),
                assigned_model=t.get("assigned_model"),
                retry_policy=RetryPolicy(**(t.get("retry_policy", {}))),
                risk_level=t.get("risk_level", "safe"),
            )
            tasks.append(node)
            dag[node.task_id] = node.depends_on

        overall_ac_data = data.get("acceptance_criteria", {})
        overall_checkpoints = [
            Checkpoint(**cp) for cp in overall_ac_data.get("checkpoints", [])
        ]

        return ExecutionPlan(
            original_request=original_request,
            tasks=tasks,
            dag=dag,
            acceptance_criteria=AcceptanceCriteria(
                description=overall_ac_data.get("description", ""),
                checkpoints=overall_checkpoints,
            ),
            estimated_duration=data.get("estimated_duration", 0),
            risk_assessment=data.get("risk_assessment", ""),
        )

    async def _validate_feasibility(self, plan: ExecutionPlan) -> list[str]:
        issues = []
        for task in plan.tasks:
            if task.module_id not in self.registry:
                issues.append(f"Task {task.task_id}: module '{task.module_id}' not registered")
            else:
                mod = self.registry.get_or_raise(task.module_id)
                valid, msg = await mod.validate_params(task.action, task.params)
                if not valid:
                    issues.append(f"Task {task.task_id}: {msg}")
        return issues
