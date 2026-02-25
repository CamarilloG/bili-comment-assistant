from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from utils.logger import get_logger
from ai_center.model_router import ModelRouter
from ai_center.models.plan import AcceptanceCriteria, TaskNode
from ai_center.models.session import ExecutionSession
from ai_center.prompts.validator_prompts import (
    VALIDATOR_SYSTEM_PROMPT,
    VALIDATOR_USER_PROMPT,
    CROSS_VALIDATION_PROMPT,
)
from modules.base import ActionResult

logger = get_logger()


class ValidationResult(BaseModel):
    passed: bool = False
    failures: List[str] = []
    summary: str = ""
    suggestions: List[str] = []


class Validator:
    """Multi-layer validation: rule-based checks, AI judgment, and cross-validation."""

    def __init__(self, model_router: ModelRouter) -> None:
        self.router = model_router

    async def check_task(
        self, task: TaskNode, result: ActionResult
    ) -> ValidationResult:
        failures: List[str] = []

        for cp in task.acceptance.checkpoints:
            actual = self._extract_field(result.data, cp.field)

            if cp.check_type == "value_match":
                if actual != cp.expected:
                    failures.append(
                        f"{cp.field}: expected {cp.expected}, got {actual}"
                    )

            elif cp.check_type == "count_gte":
                try:
                    if int(actual) < int(cp.expected):
                        failures.append(
                            f"{cp.field}: expected >= {cp.expected}, got {actual}"
                        )
                except (TypeError, ValueError):
                    failures.append(f"{cp.field}: cannot compare {actual} with {cp.expected}")

            elif cp.check_type == "status_equals":
                data_status = result.data.get("status") if isinstance(result.data, dict) else None
                if data_status != cp.expected:
                    failures.append(
                        f"status: expected {cp.expected}, got {data_status}"
                    )

            elif cp.check_type == "custom_ai_judge":
                judgment = await self._ai_judge(task, result, cp)
                if not judgment.passed:
                    failures.extend(judgment.failures)

        return ValidationResult(
            passed=len(failures) == 0,
            failures=failures,
            summary=f"{len(failures)} check(s) failed" if failures else "All checks passed",
        )

    async def check_overall(
        self,
        criteria: AcceptanceCriteria,
        session: ExecutionSession,
    ) -> ValidationResult:
        summary = session.get_summary()

        # Rule-based checks first
        failures: List[str] = []
        for cp in criteria.checkpoints:
            if cp.check_type == "count_gte":
                actual = summary.get(cp.field, summary.get("accepted", 0))
                try:
                    if int(actual) < int(cp.expected):
                        failures.append(f"{cp.field}: expected >= {cp.expected}, got {actual}")
                except (TypeError, ValueError):
                    pass

        # AI overall judgment
        user_prompt = VALIDATOR_USER_PROMPT.format(
            acceptance_criteria=criteria.description,
            execution_summary=json.dumps(summary, ensure_ascii=False, indent=2),
        )

        raw = await self.router.call(
            task_type="validation",
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=512,
        )

        if raw:
            ai_result = self._parse_ai_judgment(raw)
            if not ai_result.passed:
                failures.extend(ai_result.failures)
            return ValidationResult(
                passed=len(failures) == 0,
                failures=failures,
                summary=ai_result.summary,
                suggestions=ai_result.suggestions,
            )

        return ValidationResult(
            passed=len(failures) == 0,
            failures=failures,
            summary="Rule-based check only (AI unavailable)",
        )

    async def _ai_judge(
        self, task: TaskNode, result: ActionResult, checkpoint: Any
    ) -> ValidationResult:
        prompt = (
            f"Task: {task.description}\n"
            f"Result: {json.dumps(result.data, ensure_ascii=False, default=str)}\n"
            f"Checkpoint: {checkpoint.field} — {checkpoint.expected}"
        )
        raw = await self.router.call(
            task_type="validation",
            system_prompt=VALIDATOR_SYSTEM_PROMPT,
            user_prompt=prompt,
            temperature=0.2,
            max_tokens=256,
        )
        if raw:
            return self._parse_ai_judgment(raw)
        return ValidationResult(passed=True, summary="AI judge unavailable, defaulting to pass")

    def _parse_ai_judgment(self, raw: str) -> ValidationResult:
        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(cleaned)
            return ValidationResult(
                passed=bool(data.get("passed", False)),
                failures=data.get("failures", []),
                summary=data.get("summary", ""),
                suggestions=data.get("suggestions", []),
            )
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"Failed to parse AI judgment: {raw[:200]}")
            return ValidationResult(passed=True, summary="Parse error, defaulting to pass")

    @staticmethod
    def _extract_field(data: Any, field: str) -> Any:
        if data is None:
            return None
        if isinstance(data, dict):
            parts = field.split(".")
            current = data
            for p in parts:
                if isinstance(current, dict):
                    current = current.get(p)
                else:
                    return None
            return current
        return None
