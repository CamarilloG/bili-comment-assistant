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


class CaptchaModule(IModule):
    """Wraps core.captcha_tracker + core.captcha_check as a standardised IModule."""

    def __init__(self) -> None:
        self._tracker = None
        self._page = None

    def set_page(self, page: Any) -> None:
        self._page = page

    def _get_tracker(self) -> Any:
        if self._tracker is None:
            from core.captcha_tracker import CaptchaTracker
            self._tracker = CaptchaTracker()
        return self._tracker

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="captcha",
            description="验证码管理模块，检测页面验证码、记录触发次数、计算冷却时长",
            actions=[
                ActionSpec(
                    name="check_page_captcha",
                    description="检查当前页面是否存在验证码弹窗",
                    returns={"has_captcha": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="record_captcha_event",
                    description="记录一次验证码触发事件",
                    returns={"today_count": "int"},
                    side_effects=["modifies captcha record"],
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_cooldown",
                    description="根据今日触发次数计算冷却时长",
                    parameters={
                        "base_minutes": ParamSpec(type="int", description="基础冷却分钟数", required=False, default=30),
                    },
                    returns={"cooldown_minutes": "int"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_today_stats",
                    description="获取今日验证码统计",
                    returns={"count": "int", "date": "str"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="system",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)

        try:
            if action == "check_page_captcha":
                if self._page is None:
                    return ActionResult(success=False, error="Page not set")
                from core.captcha_check import check_captcha_on_page
                has = check_captcha_on_page(self._page)
                return ActionResult(success=True, data={"has_captcha": has})

            tracker = self._get_tracker()

            if action == "record_captcha_event":
                count = tracker.record()
                return ActionResult(success=True, data={"today_count": count})

            if action == "get_cooldown":
                base = params.get("base_minutes", 30)
                minutes = tracker.get_cooldown_minutes(base)
                return ActionResult(success=True, data={"cooldown_minutes": minutes})

            if action == "get_today_stats":
                count = tracker.get_today_count()
                return ActionResult(
                    success=True,
                    data={"count": count, "date": tracker._today()},
                )

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        return True, ""

    async def health_check(self) -> bool:
        return True
