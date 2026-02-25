from __future__ import annotations

from typing import Dict, Optional, Set

from ai_center.event_bus import EventBus
from ai_center.models.events import EventType, TaskEvent


# Valid state transitions
_TRANSITIONS: Dict[str, Set[str]] = {
    "pending":    {"running"},
    "running":    {"checking", "failed", "paused"},
    "checking":   {"accepted", "retrying"},
    "accepted":   set(),
    "failed":     {"retrying", "terminated"},
    "retrying":   {"running"},
    "paused":     {"running", "terminated"},
    "terminated": set(),
}


class InvalidTransition(Exception):
    pass


class TaskStateMachine:
    """Manages per-task state, enforcing valid transitions and emitting events."""

    def __init__(self, event_bus: Optional[EventBus] = None) -> None:
        self._states: Dict[str, str] = {}  # task_id -> current state
        self._event_bus = event_bus

    def register(self, task_id: str, initial: str = "pending") -> None:
        self._states[task_id] = initial

    def get_state(self, task_id: str) -> str:
        return self._states.get(task_id, "pending")

    async def transition(
        self,
        task_id: str,
        new_state: str,
        session_id: str = "",
        reason: str = "",
    ) -> str:
        current = self._states.get(task_id, "pending")
        allowed = _TRANSITIONS.get(current, set())
        if new_state not in allowed:
            raise InvalidTransition(
                f"Cannot transition task '{task_id}' from '{current}' to '{new_state}'"
            )

        self._states[task_id] = new_state

        if self._event_bus:
            event_map = {
                "running": EventType.TASK_START,
                "checking": EventType.TASK_COMPLETED,
                "accepted": EventType.VALIDATION_RESULT,
                "failed": EventType.TASK_FAILED,
                "paused": EventType.CAPTCHA_DETECTED,
            }
            etype = event_map.get(new_state, EventType.TASK_PROGRESS)
            await self._event_bus.emit(
                TaskEvent(
                    event_type=etype,
                    session_id=session_id,
                    task_id=task_id,
                    data={"from": current, "to": new_state, "reason": reason},
                    message=f"Task {task_id}: {current} -> {new_state}",
                )
            )

        return new_state

    def is_terminal(self, task_id: str) -> bool:
        return self._states.get(task_id) in ("accepted", "terminated")

    def all_terminal(self) -> bool:
        return all(s in ("accepted", "terminated") for s in self._states.values())
