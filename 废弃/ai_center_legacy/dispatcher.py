from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Dict, List, Optional

from utils.logger import get_logger
from modules.base import ActionResult, ExecutionContext
from modules.registry import ModuleRegistry
from modules.browser_pool import BrowserPool
from ai_center.models.plan import ExecutionPlan, TaskNode
from ai_center.models.events import EventType, TaskEvent
from ai_center.event_bus import EventBus

logger = get_logger()


class Dispatcher:
    """Schedules tasks from an ExecutionPlan according to DAG topology.

    Same-layer tasks with no mutual dependencies run concurrently.
    Browser resources are acquired/released automatically.
    """

    def __init__(
        self,
        module_registry: ModuleRegistry,
        browser_pool: Optional[BrowserPool] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        self.registry = module_registry
        self.browser_pool = browser_pool
        self.event_bus = event_bus
        self._task_results: Dict[str, Any] = {}

    async def dispatch(
        self,
        plan: ExecutionPlan,
        session_id: str = "",
    ) -> AsyncGenerator[TaskEvent, None]:
        layers = plan.topological_layers()
        self._task_results = {}

        shared_browser_meta = None
        shared_ctx = None
        shared_page = None
        def _plan_needs_browser() -> bool:
            for t in plan.tasks:
                mod = self.registry.get(t.module_id)
                if not mod:
                    continue
                if mod.get_capability().requires_browser:
                    return True
                if t.module_id == "captcha" and t.action == "check_page_captcha":
                    return True
            return False

        if self.browser_pool and _plan_needs_browser():
            shared_browser_meta = await self.browser_pool.acquire()
            shared_ctx = self.browser_pool.get_context(shared_browser_meta.id)
            shared_page = await shared_ctx.new_page()
        try:
            for layer_idx, layer in enumerate(layers):
                tasks = [plan.get_task(tid) for tid in layer]
                logger.info(f"Dispatching layer {layer_idx}: {[t.task_id for t in tasks]}")

                coros = [
                    self._execute_task(t, session_id, shared_ctx, shared_page, shared_browser_meta)
                    for t in tasks
                ]
                results = await asyncio.gather(*coros, return_exceptions=True)

                for task, result in zip(tasks, results):
                    if isinstance(result, Exception):
                        event = TaskEvent(
                            event_type=EventType.TASK_FAILED,
                            session_id=session_id,
                            task_id=task.task_id,
                            data={"error": str(result)},
                            message=f"Task {task.task_id} raised exception",
                        )
                    elif isinstance(result, ActionResult):
                        self._task_results[task.task_id] = result.data
                        etype = EventType.TASK_COMPLETED if result.success else EventType.TASK_FAILED
                        event = TaskEvent(
                            event_type=etype,
                            session_id=session_id,
                            task_id=task.task_id,
                            data={"result": result.model_dump()},
                            message=f"Task {task.task_id}: {'success' if result.success else 'failed'}",
                        )
                    else:
                        event = TaskEvent(
                            event_type=EventType.TASK_FAILED,
                            session_id=session_id,
                            task_id=task.task_id,
                            data={"error": "Unknown result type"},
                        )

                    if self.event_bus:
                        await self.event_bus.emit(event)
                    yield event
        finally:
            if shared_page:
                try:
                    await shared_page.close()
                except Exception:
                    pass
            if shared_browser_meta and self.browser_pool:
                await self.browser_pool.release(shared_browser_meta.id)

    async def _execute_task(
        self,
        task: TaskNode,
        session_id: str,
        shared_ctx: Any = None,
        shared_page: Any = None,
        shared_browser_meta: Any = None,
    ) -> ActionResult:
        module = self.registry.get(task.module_id)
        if module is None:
            return ActionResult(success=False, error=f"Module '{task.module_id}' not found")

        resolved_params = self._resolve_params(task.params)

        cap = module.get_capability()
        use_shared = shared_ctx is not None and shared_page is not None
        needs_browser = cap.requires_browser or (
            task.module_id == "captcha" and task.action == "check_page_captcha"
        )

        if needs_browser and use_shared:
            if hasattr(module, "set_browser_context"):
                module.set_browser_context(shared_ctx)
            if hasattr(module, "set_page"):
                module.set_page(shared_page)

        ctx = ExecutionContext(
            session_id=session_id,
            task_id=task.task_id,
            browser_id=shared_browser_meta.id if shared_browser_meta else None,
        )

        try:
            if self.event_bus:
                await self.event_bus.emit_simple(
                    EventType.TASK_START,
                    session_id=session_id,
                    task_id=task.task_id,
                    message=f"Starting {task.module_id}.{task.action}",
                )

            result = await module.execute(task.action, resolved_params, ctx)
            return result

        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def _resolve_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Replace ${task_id.data.field} references with actual values from completed tasks."""
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]  # e.g. "t1.data.videos"
                parts = ref.split(".", 1)
                task_id = parts[0]
                field_path = parts[1] if len(parts) > 1 else ""
                task_data = self._task_results.get(task_id)
                if task_data is not None and field_path:
                    for fp in field_path.split("."):
                        if isinstance(task_data, dict):
                            task_data = task_data.get(fp)
                        else:
                            break
                resolved[key] = task_data
            else:
                resolved[key] = value
        return resolved
