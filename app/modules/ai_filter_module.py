from __future__ import annotations

from typing import Any, Dict, List

from modules.base import (
    ActionResult,
    ActionSpec,
    ExecutionContext,
    IModule,
    ModuleCapability,
    ParamSpec,
)


class AIFilterModule(IModule):
    """Wraps the video-filtering part of core.ai_manager.AIManager."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def set_config(self, config: Dict[str, Any]) -> None:
        self._config = config

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="ai_filter",
            description="AI视频筛选模块，根据自定义标准判断视频是否适合评论",
            actions=[
                ActionSpec(
                    name="check_relevance",
                    description="判断单个视频是否与标准匹配",
                    parameters={
                        "video_info": ParamSpec(type="dict", description="视频信息"),
                        "criteria": ParamSpec(type="string", description="筛选标准（自然语言）"),
                    },
                    returns={"keep": "bool", "reason": "str"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="batch_filter",
                    description="批量筛选多个视频",
                    parameters={
                        "video_list": ParamSpec(type="list", description="视频信息列表"),
                        "criteria": ParamSpec(type="string", description="筛选标准"),
                    },
                    returns={"results": "list of {bv, keep, reason}"},
                    estimated_duration="slow",
                    risk_level="safe",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="ai_generation",
        )

    def _build_manager(self, criteria: str) -> Any:
        from core.ai_manager import AIManager
        import copy

        cfg = copy.deepcopy(self._config)
        ai_section = cfg.get("ai", {})
        ai_section["enabled"] = True
        filter_section = ai_section.get("filter", {})
        filter_section["enabled"] = True
        filter_section["criteria"] = criteria
        ai_section["filter"] = filter_section
        cfg["ai"] = ai_section
        return AIManager(cfg)

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)

        try:
            criteria = params.get("criteria", "")
            mgr = self._build_manager(criteria)

            if action == "check_relevance":
                keep, reason = mgr.check_video_relevance(params["video_info"])
                return ActionResult(success=True, data={"keep": keep, "reason": reason})

            if action == "batch_filter":
                # TODO: 添加取消机制 - 需要在 ExecutionContext 中添加 stop_event
                # 当前实现：批量操作无法中途取消
                results: List[Dict[str, Any]] = []
                for v in params["video_list"]:
                    keep, reason = mgr.check_video_relevance(v)
                    results.append({"bv": v.get("bv", ""), "keep": keep, "reason": reason})
                return ActionResult(success=True, data={"results": results})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "check_relevance":
            if not params.get("video_info"):
                return False, "video_info is required"
            if not params.get("criteria"):
                return False, "criteria is required"
        if action == "batch_filter":
            if not params.get("video_list"):
                return False, "video_list is required"
            if not params.get("criteria"):
                return False, "criteria is required"
        return True, ""

    async def health_check(self) -> bool:
        from core.models_registry import get_model_by_id
        model_id = self._config.get("ai", {}).get("model_id")
        model_cfg = get_model_by_id(model_id) if model_id else None
        return bool(model_cfg and (model_cfg.get("api_key") or "").strip())
