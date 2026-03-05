"""Bot module — registered in ModuleRegistry for discovery and lifecycle management."""

from __future__ import annotations

from typing import Any, Dict

from modules.base import IModule, ModuleCapability, ActionResult, ExecutionContext, ActionSpec
from utils.logger import get_logger

logger = get_logger()


class BotModule(IModule):
    """Thin wrapper exposing bot adapters through the module system.

    This module is intentionally minimal (skeleton).  It will be fleshed out
    once actual platform SDKs are integrated.
    """

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="bot",
            description="Enterprise WeChat and QQ bot adapter skeleton",
            actions=[
                ActionSpec(
                    name="status",
                    description="Report adapter status",
                    parameters={},
                    returns={"wecom": "str", "qqbot": "str"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="integration",
        )

    async def execute(self, action: str, params: Dict[str, Any], context: ExecutionContext) -> ActionResult:
        self._require_action(action)
        if action == "status":
            return ActionResult(success=True, data={"wecom": "stub", "qqbot": "stub"})
        return ActionResult(success=False, error=f"Unknown action: {action}")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        return True, ""

    async def health_check(self) -> bool:
        return True
