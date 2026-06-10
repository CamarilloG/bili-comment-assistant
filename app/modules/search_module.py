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


class SearchModule(IModule):
    """Wraps core.search.SearchManager as a standardised IModule."""

    def __init__(self) -> None:
        self._page = None

    def set_page(self, page: Any) -> None:
        self._page = page

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="search",
            description="B站视频搜索模块，可按关键词搜索视频并翻页",
            actions=[
                ActionSpec(
                    name="search_videos",
                    description="按关键词搜索视频，返回视频列表",
                    parameters={
                        "keyword": ParamSpec(type="string", description="搜索关键词"),
                        "max_count": ParamSpec(type="int", description="最大返回数量", required=False, default=20),
                        "order": ParamSpec(
                            type="string", description="排序方式",
                            required=False, default="pubdate",
                            enum=["totalrank", "pubdate", "click", "dm", "stow"],
                        ),
                        "duration": ParamSpec(type="int", description="时长筛选", required=False, default=0),
                        "time_range": ParamSpec(type="dict", description="时间范围筛选", required=False),
                    },
                    returns={"videos": "list of {url, bv, title, author, date, views, comments}"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_current_page_videos",
                    description="提取当前搜索结果页的视频",
                    parameters={
                        "max_count": ParamSpec(type="int", description="最大返回数量", required=False, default=20),
                    },
                    returns={"videos": "list"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="go_to_next_page",
                    description="翻到下一页搜索结果",
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
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)
        if self._page is None:
            return ActionResult(success=False, error="Page not set")

        from core.search import SearchManager

        try:
            mgr = SearchManager(self._page)

            if action == "search_videos":
                videos = mgr.search_videos(
                    keyword=params["keyword"],
                    max_count=params.get("max_count", 20),
                    order=params.get("order", "pubdate"),
                    duration=params.get("duration", 0),
                    time_range=params.get("time_range"),
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
