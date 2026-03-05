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


class CommentModule(IModule):
    """Wraps core.comment.CommentManager as a standardised IModule."""

    def __init__(self) -> None:
        self._page = None

    def set_page(self, page: Any) -> None:
        self._page = page

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="comment",
            description="B站评论发布模块，支持文本和图片评论",
            actions=[
                ActionSpec(
                    name="post_comment",
                    description="在指定视频下发布评论",
                    parameters={
                        "url": ParamSpec(type="string", description="视频URL"),
                        "text": ParamSpec(type="string", description="评论文本"),
                        "image_path": ParamSpec(type="string", description="评论图片路径", required=False),
                    },
                    returns={"status": "success|captcha|failed"},
                    side_effects=["posts a comment"],
                    estimated_duration="medium",
                    risk_level="moderate",
                ),
                ActionSpec(
                    name="check_captcha",
                    description="检查当前页面是否出现验证码弹窗",
                    returns={"has_captcha": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
            ],
            requires_browser=True,
            requires_auth=True,
            category="browser_automation",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)
        if self._page is None:
            return ActionResult(success=False, error="Page not set")

        from core.comment import CommentManager

        try:
            mgr = CommentManager(self._page)

            if action == "post_comment":
                result, toast_message = mgr.post_comment(
                    url=params["url"],
                    text=params["text"],
                    image_path=params.get("image_path"),
                )
                return ActionResult(
                    success=(result == "success"),
                    data={"status": result, "message": toast_message},
                )

            if action == "check_captcha":
                has = mgr._check_captcha()
                return ActionResult(success=True, data={"has_captcha": has})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "post_comment":
            if not params.get("url"):
                return False, "url is required"
            if not params.get("text"):
                return False, "text is required"
        return True, ""

    async def health_check(self) -> bool:
        return self._page is not None
