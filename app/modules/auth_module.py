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


class AuthModule(IModule):
    """Wraps core.auth.AuthManager as a standardised IModule."""

    def __init__(self) -> None:
        self._browser_context = None

    def set_browser_context(self, context: Any) -> None:
        self._browser_context = context

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="auth",
            description="B站账号认证模块，支持Cookie登录和扫码登录",
            actions=[
                ActionSpec(
                    name="login_with_cookies",
                    description="使用本地Cookie文件登录",
                    parameters={
                        "cookie_file": ParamSpec(
                            type="string",
                            description="Cookie文件路径",
                            required=False,
                            default="cookies.json",
                        )
                    },
                    returns={"logged_in": "bool"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="login_with_qrcode",
                    description="通过扫描二维码登录",
                    returns={"logged_in": "bool", "qr_image_path": "str"},
                    estimated_duration="slow",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="check_login_status",
                    description="检查当前是否处于登录状态",
                    returns={"logged_in": "bool"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="save_cookies",
                    description="保存当前Cookie到文件",
                    parameters={
                        "path": ParamSpec(
                            type="string",
                            description="保存路径",
                            required=False,
                            default="cookies.json",
                        )
                    },
                    returns={"saved": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
            ],
            requires_browser=True,
            requires_auth=False,
            category="system",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)
        if self._browser_context is None:
            return ActionResult(success=False, error="Browser context not set")

        from core.auth import AuthManager

        try:
            cookie_file = params.get("cookie_file", "cookies.json")
            mgr = AuthManager(self._browser_context, cookie_file)

            if action == "login_with_cookies":
                ok = await mgr.login()
                return ActionResult(success=ok, data={"logged_in": ok})

            if action == "login_with_qrcode":
                ok = await mgr._qr_login()
                return ActionResult(
                    success=ok,
                    data={"logged_in": ok, "qr_image_path": "login_qrcode.png"},
                )

            if action == "check_login_status":
                ok = await mgr._check_login_status()
                return ActionResult(success=True, data={"logged_in": ok})

            if action == "save_cookies":
                path = params.get("path", "cookies.json")
                mgr.cookie_file = path
                await mgr._save_cookies()
                return ActionResult(success=True, data={"saved": True})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        return True, ""

    async def health_check(self) -> bool:
        return self._browser_context is not None
