from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class EventType(str, Enum):
    PLAN_READY = "plan_ready"
    PLAN_MODIFIED = "plan_modified"
    ROUND_START = "round_start"
    ROUND_END = "round_end"
    TASK_START = "task_start"
    TASK_PROGRESS = "task_progress"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    VALIDATION_START = "validation_start"
    VALIDATION_RESULT = "validation_result"
    CAPTCHA_DETECTED = "captcha_detected"
    BROWSER_EVENT = "browser_event"
    FINAL_REPORT = "final_report"
    ERROR = "error"


class TaskEvent(BaseModel):
    """Unified event payload emitted by the control center."""

    event_type: EventType
    session_id: str = ""
    task_id: str = ""
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None
