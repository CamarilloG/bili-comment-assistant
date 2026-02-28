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


class AIGenModule(IModule):
    """Wraps the comment-generation part of core.ai_manager.AIManager."""

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self._config = config or {}

    def set_config(self, config: Dict[str, Any]) -> None:
        self._config = config

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="ai_gen",
            description="AI评论生成模块，根据视频信息生成自然评论文本",
            actions=[
                ActionSpec(
                    name="generate_comment",
                    description="为单个视频生成AI评论",
                    parameters={
                        "video_info": ParamSpec(type="dict", description="视频信息 {title, author, ...}"),
                        "persona": ParamSpec(type="string", description="用户人设/推广意图", required=False, default=""),
                        "style": ParamSpec(type="string", description="评论风格", required=False, default="casual"),
                        "max_length": ParamSpec(type="int", description="最大字数", required=False, default=100),
                    },
                    returns={"comment": "str"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="generate_batch_comments",
                    description="批量为多个视频生成AI评论",
                    parameters={
                        "video_list": ParamSpec(type="list", description="视频信息列表"),
                        "persona": ParamSpec(type="string", description="用户人设", required=False, default=""),
                        "style": ParamSpec(type="string", description="评论风格", required=False, default="casual"),
                    },
                    returns={"comments": "list of {bv, comment}"},
                    estimated_duration="slow",
                    risk_level="safe",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="ai_generation",
        )

    def _build_manager(self, params: Dict[str, Any]) -> Any:
        from core.ai_manager import AIManager

        cfg = dict(self._config)
        ai_section = dict(cfg.get("ai", {}))
        ai_section["enabled"] = True
        comment_section = dict(ai_section.get("comment", {}))
        comment_section["enabled"] = True
        if params.get("persona"):
            comment_section["user_intent"] = params["persona"]
        if params.get("style"):
            comment_section["style"] = params["style"]
        if params.get("max_length"):
            comment_section["max_length"] = params["max_length"]
        ai_section["comment"] = comment_section
        cfg["ai"] = ai_section
        return AIManager(cfg)

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)

        try:
            mgr = self._build_manager(params)

            if action == "generate_comment":
                text = mgr.generate_comment(params["video_info"])
                if text:
                    return ActionResult(success=True, data={"comment": text})
                return ActionResult(success=False, error="AI comment generation returned empty")

            if action == "generate_batch_comments":
                results: List[Dict[str, str]] = []
                for v in params["video_list"]:
                    text = mgr.generate_comment(v)
                    results.append({"bv": v.get("bv", ""), "comment": text or ""})
                return ActionResult(success=True, data={"comments": results})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "generate_comment" and not params.get("video_info"):
            return False, "video_info is required"
        if action == "generate_batch_comments" and not params.get("video_list"):
            return False, "video_list is required"
        return True, ""

    async def health_check(self) -> bool:
        from core.models_registry import get_model_by_id
        model_id = self._config.get("ai", {}).get("model_id")
        model_cfg = get_model_by_id(model_id) if model_id else None
        return bool(model_cfg and (model_cfg.get("api_key") or "").strip())
