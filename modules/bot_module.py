"""Bot module — registered in ModuleRegistry for discovery and lifecycle management."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from modules.base import IModule, ModuleCapability, ActionResult
from utils.logger import get_logger

logger = get_logger()


class BotModule(IModule):
    """Thin wrapper exposing bot adapters through the module system.

    This module is intentionally minimal (skeleton).  It will be fleshed out
    once actual platform SDKs are integrated.
    """

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            module_id="bot",
            name="Bot Integrations",
            description="Enterprise WeChat and QQ bot adapter skeleton",
            actions=[
                {"name": "status", "description": "Report adapter status"},
            ],
            parameters=[],
        )

    async def execute(self, action: str, params: Dict[str, Any]) -> ActionResult:
        if action == "status":
            return ActionResult(success=True, data={"wecom": "stub", "qqbot": "stub"})
        return ActionResult(success=False, error=f"Unknown action: {action}")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> Optional[str]:
        return None

    async def health_check(self) -> bool:
        return True
