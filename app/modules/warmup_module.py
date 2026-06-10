from __future__ import annotations

from typing import Any, Dict

from modules.base import (
    ActionResult,
    ActionSpec,
    ExecutionContext,
    IModule,
    ModuleCapability,
    ParamSpec,
)


class WarmupModule(IModule):
    """Wraps core.warmup.WarmupManager as a standardised IModule."""

    def __init__(self) -> None:
        self._browser_context = None
        self._config: Dict[str, Any] = {}

    def set_browser_context(self, context: Any) -> None:
        self._browser_context = context

    def set_config(self, config: Dict[str, Any]) -> None:
        self._config = config

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="warmup",
            description="B站账号养号模块，模拟真人浏览行为（观看、点赞、滚动）",
            actions=[
                ActionSpec(
                    name="run_warmup",
                    description="执行养号任务，随机观看视频并模拟互动",
                    parameters={
                        "duration_minutes": ParamSpec(type="int", description="养号时长（分钟）", required=False, default=30),
                        "max_videos": ParamSpec(type="int", description="最大观看视频数", required=False, default=20),
                    },
                    returns={"stats": "{watched, time, likes}"},
                    estimated_duration="slow",
                    risk_level="safe",
                ),
                # FIXME: watch_single_video 和 like_video 暂时禁用（同步/异步混用问题）
                # ActionSpec(name="watch_single_video", ...),
                # ActionSpec(name="like_video", ...),
            ],
            requires_browser=True,
            requires_auth=True,
            category="browser_automation",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)
        if self._browser_context is None:
            return ActionResult(success=False, error="Browser context not set")

        from core.warmup import WarmupManager

        try:
            if action == "run_warmup":
                mgr = WarmupManager(self._browser_context, self._config)
                duration = params.get("duration_minutes", 30)
                mgr.run(duration_override=duration)
                return ActionResult(
                    success=True,
                    data={
                        "stats": {
                            "watched": mgr.watched_count,
                            "time": round(mgr.total_time_seconds / 60, 1),
                            "likes": mgr.like_count,
                        }
                    },
                )

            # FIXME: watch_single_video 和 like_video 混用了同步/异步 Playwright API
            # WarmupManager 使用同步 API，但这里使用 await，需要重构
            # if action == "watch_single_video":
            #     ...
            # if action == "like_video":
            #     ...

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action in ("watch_single_video", "like_video") and not params.get("url"):
            return False, "url is required"
        return True, ""

    async def health_check(self) -> bool:
        return self._browser_context is not None
