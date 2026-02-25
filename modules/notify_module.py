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


class NotifyModule(IModule):
    """Wraps core.notifier.CaptchaNotifier as a standardised IModule."""

    def __init__(self) -> None:
        self._notifier = None

    def _get_notifier(self) -> Any:
        if self._notifier is None:
            from core.notifier import CaptchaNotifier
            self._notifier = CaptchaNotifier()
        return self._notifier

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="notify",
            description="通知模块，在触发验证码或异常时发送通知",
            actions=[
                ActionSpec(
                    name="notify_captcha",
                    description="发送验证码触发通知",
                    parameters={
                        "count": ParamSpec(type="int", description="今日第几次触发"),
                        "cooldown_minutes": ParamSpec(type="int", description="冷却时长"),
                        "quiet_minutes": ParamSpec(type="int", description="静默时长", required=False, default=5),
                    },
                    returns={"notified": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="notify_terminated",
                    description="发送任务终止通知",
                    parameters={
                        "count": ParamSpec(type="int", description="今日触发次数"),
                        "max_count": ParamSpec(type="int", description="上限次数"),
                    },
                    returns={"notified": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="notify_alert",
                    description="发送风控提醒",
                    parameters={
                        "source": ParamSpec(type="string", description="触发场景"),
                        "detail": ParamSpec(type="string", description="详情", required=False, default=""),
                    },
                    returns={"notified": "bool"},
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
        notifier = self._get_notifier()

        try:
            if action == "notify_captcha":
                notifier.notify(
                    params["count"],
                    params["cooldown_minutes"],
                    params.get("quiet_minutes", 5),
                )
                return ActionResult(success=True, data={"notified": True})

            if action == "notify_terminated":
                notifier.notify_terminated(params["count"], params["max_count"])
                return ActionResult(success=True, data={"notified": True})

            if action == "notify_alert":
                notifier.notify_captcha_alert(params["source"], params.get("detail", ""))
                return ActionResult(success=True, data={"notified": True})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "notify_captcha":
            if params.get("count") is None:
                return False, "count is required"
            if params.get("cooldown_minutes") is None:
                return False, "cooldown_minutes is required"
        if action == "notify_terminated":
            if params.get("count") is None or params.get("max_count") is None:
                return False, "count and max_count are required"
        if action == "notify_alert" and not params.get("source"):
            return False, "source is required"
        return True, ""

    async def health_check(self) -> bool:
        return True
