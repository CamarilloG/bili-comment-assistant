from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set

from utils.logger import get_logger
from ai_center.models.events import EventType, TaskEvent

logger = get_logger()

Listener = Callable[[TaskEvent], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus.

    * In-process listeners subscribe via ``on(event_type, callback)``.
    * WebSocket connections are registered per session; events matching
      the session are forwarded automatically.
    """

    def __init__(self) -> None:
        self._listeners: Dict[EventType, List[Listener]] = {}
        self._global_listeners: List[Listener] = []
        # session_id -> set of asyncio.Queue (one per ws connection)
        self._ws_queues: Dict[str, Set[asyncio.Queue]] = {}

    # ---- subscription ----

    def on(self, event_type: EventType, callback: Listener) -> None:
        self._listeners.setdefault(event_type, []).append(callback)

    def on_all(self, callback: Listener) -> None:
        self._global_listeners.append(callback)

    def off(self, event_type: EventType, callback: Listener) -> None:
        listeners = self._listeners.get(event_type, [])
        if callback in listeners:
            listeners.remove(callback)

    # ---- websocket registration ----

    def register_ws(self, session_id: str, queue: asyncio.Queue) -> None:
        self._ws_queues.setdefault(session_id, set()).add(queue)

    def unregister_ws(self, session_id: str, queue: asyncio.Queue) -> None:
        qs = self._ws_queues.get(session_id)
        if qs:
            qs.discard(queue)
            if not qs:
                del self._ws_queues[session_id]

    # ---- emit ----

    async def emit(self, event: TaskEvent) -> None:
        # typed listeners
        for cb in self._listeners.get(event.event_type, []):
            try:
                await cb(event)
            except Exception as exc:
                logger.error(f"EventBus listener error: {exc}")

        # global listeners
        for cb in self._global_listeners:
            try:
                await cb(event)
            except Exception as exc:
                logger.error(f"EventBus global listener error: {exc}")

        # push to websocket queues
        if event.session_id:
            for q in self._ws_queues.get(event.session_id, set()):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("WebSocket queue full, dropping event")

    async def emit_simple(
        self,
        event_type: EventType,
        session_id: str = "",
        task_id: str = "",
        message: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        event = TaskEvent(
            event_type=event_type,
            session_id=session_id,
            task_id=task_id,
            message=message,
            data=data or {},
        )
        await self.emit(event)
