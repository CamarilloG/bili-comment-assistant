# 抖音网站自动化模块（IModule），与 B 站 search/comment 等业务完全独立。
# 仅注册为独立 capability，供需要操作抖音网页时使用。

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


class DouyinModule(IModule):
    """抖音网页版自动化：搜索视频、当前页列表、翻页。与 B 站模块无耦合。"""

    def __init__(self) -> None:
        self._page = None

    def set_page(self, page: Any) -> None:
        self._page = page

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="douyin",
            description="抖音网页版自动化：按关键词搜索视频、获取当前页列表、翻页",
            actions=[
                ActionSpec(
                    name="search_videos",
                    description="在抖音网页版按关键词搜索视频，返回视频列表",
                    parameters={
                        "keyword": ParamSpec(type="string", description="搜索关键词"),
                        "max_count": ParamSpec(
                            type="int",
                            description="最大返回数量",
                            required=False,
                            default=20,
                        ),
                    },
                    returns={"videos": "list of {url, title, author, platform}"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_current_page_videos",
                    description="提取当前抖音搜索结果页的视频列表",
                    parameters={
                        "max_count": ParamSpec(
                            type="int",
                            description="最大返回数量",
                            required=False,
                            default=20,
                        ),
                    },
                    returns={"videos": "list"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="go_to_next_page",
                    description="翻到抖音搜索结果下一页",
                    parameters={},
                    returns={"success": "bool", "has_next": "bool"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
            ],
            requires_browser=True,
            requires_auth=False,
            category="browser_automation",
        )

    async def execute(
        self,
        action: str,
        params: Dict[str, Any],
        context: ExecutionContext,
    ) -> ActionResult:
        self._require_action(action)
        if self._page is None:
            return ActionResult(success=False, error="Page not set")

        # 默认注入本地保存的抖音 Cookie，后续请求自动携带登录态
        try:
            from douyin.auth import inject_douyin_cookies_to_page
            inject_douyin_cookies_to_page(self._page)
        except Exception:
            pass

        from douyin.search import DouyinSearchManager

        try:
            mgr = DouyinSearchManager(self._page)
            if action == "search_videos":
                videos = mgr.search_videos(
                    keyword=params["keyword"],
                    max_count=params.get("max_count", 20),
                )
                return ActionResult(success=True, data={"videos": videos})
            if action == "get_current_page_videos":
                videos = mgr.get_current_page_videos(params.get("max_count", 20))
                return ActionResult(success=True, data={"videos": videos})
            if action == "go_to_next_page":
                ok = mgr.go_to_next_page()
                return ActionResult(success=ok, data={"success": ok, "has_next": ok})
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))
        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "search_videos" and not params.get("keyword"):
            return False, "keyword is required"
        return True, ""

    async def health_check(self) -> bool:
        return self._page is not None
