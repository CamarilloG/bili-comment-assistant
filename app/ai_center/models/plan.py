from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Checkpoint(BaseModel):
    """A single verifiable check within acceptance criteria."""

    check_type: str  # "value_match", "count_gte", "status_equals", "custom_ai_judge"
    field: str
    expected: Any = None
    tolerance: Optional[float] = None


class AcceptanceCriteria(BaseModel):
    """Acceptance criteria composed of checkpoints and a human-readable description."""

    description: str = ""
    checkpoints: List[Checkpoint] = Field(default_factory=list)


class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_seconds: float = 5.0
    retry_on: List[str] = Field(
        default_factory=lambda: ["error", "captcha"]
    )


class TaskNode(BaseModel):
    """A single step inside an execution plan."""

    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    module_id: str = ""
    action: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    acceptance: AcceptanceCriteria = Field(default_factory=AcceptanceCriteria)
    assigned_model: Optional[str] = None
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)
    risk_level: str = "safe"


class ExecutionPlan(BaseModel):
    """The full plan produced by the Planner for a user request."""

    plan_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    original_request: str = ""
    tasks: List[TaskNode] = Field(default_factory=list)
    dag: Dict[str, List[str]] = Field(default_factory=dict)
    acceptance_criteria: AcceptanceCriteria = Field(default_factory=AcceptanceCriteria)
    estimated_duration: int = 0  # seconds
    risk_assessment: str = ""

    def get_task(self, task_id: str) -> TaskNode:
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        raise KeyError(f"Task '{task_id}' not found in plan")

    def topological_layers(self) -> List[List[str]]:
        """Return tasks grouped into layers by dependency order."""
        in_degree: Dict[str, int] = {t.task_id: 0 for t in self.tasks}
        children: Dict[str, List[str]] = {t.task_id: [] for t in self.tasks}
        for t in self.tasks:
            for dep in t.depends_on:
                if dep in children:
                    children[dep].append(t.task_id)
                    in_degree[t.task_id] += 1

        layers: List[List[str]] = []
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        while queue:
            layers.append(sorted(queue))
            next_queue: List[str] = []
            for tid in queue:
                for child in children[tid]:
                    in_degree[child] -= 1
                    if in_degree[child] == 0:
                        next_queue.append(child)
            queue = next_queue
        return layers
