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


class ConfigModule(IModule):
    """Wraps core.config.ConfigValidator as a standardised IModule."""

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="config",
            description="配置管理模块，加载/保存/验证YAML配置文件",
            actions=[
                ActionSpec(
                    name="load_config",
                    description="加载并验证配置文件",
                    parameters={
                        "path": ParamSpec(type="string", description="配置文件路径", required=False, default="config.yaml"),
                    },
                    returns={"config": "dict"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="save_config",
                    description="保存配置到文件",
                    parameters={
                        "config": ParamSpec(type="dict", description="配置内容"),
                        "path": ParamSpec(type="string", description="保存路径", required=False, default="config.yaml"),
                    },
                    returns={"saved": "bool"},
                    side_effects=["writes config file"],
                    estimated_duration="fast",
                    risk_level="moderate",
                ),
                ActionSpec(
                    name="validate_config",
                    description="验证配置合法性（不写入文件）",
                    parameters={
                        "config": ParamSpec(type="dict", description="待验证的配置"),
                    },
                    returns={"valid": "bool", "errors": "list[str]"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_default_config",
                    description="获取默认配置",
                    returns={"config": "dict"},
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

        from core.config import ConfigValidator

        try:
            if action == "load_config":
                path = params.get("path", "config.yaml")
                config = ConfigValidator.load_config(path)
                return ActionResult(success=True, data={"config": config})

            if action == "save_config":
                path = params.get("path", "config.yaml")
                ConfigValidator.save_config(params["config"], path)
                return ActionResult(success=True, data={"saved": True})

            if action == "validate_config":
                errors: list[str] = []
                try:
                    ConfigValidator.validate_and_fill_defaults(params["config"])
                except (ValueError, KeyError) as e:
                    errors.append(str(e))
                return ActionResult(
                    success=len(errors) == 0,
                    data={"valid": len(errors) == 0, "errors": errors},
                )

            if action == "get_default_config":
                return ActionResult(
                    success=True,
                    data={"config": ConfigValidator.DEFAULT_CONFIG},
                )

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "save_config" and not params.get("config"):
            return False, "config is required"
        if action == "validate_config" and not params.get("config"):
            return False, "config is required"
        return True, ""

    async def health_check(self) -> bool:
        return True
