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


class HistoryModule(IModule):
    """Wraps core.history.HistoryManager as a standardised IModule.

    注意：此模块的 file_path 参数默认为相对路径 "history.json"。
    在多实例环境下，调用者应使用 slot.get_history_path(slot_id) 获取绝对路径。
    """

    def __init__(self, file_path: str = "history.json") -> None:
        self._file_path = file_path
        self._mgr = None

    def _get_mgr(self) -> Any:
        if self._mgr is None:
            from core.history import HistoryManager
            self._mgr = HistoryManager(self._file_path)
        return self._mgr

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="history",
            description="已评论视频历史记录模块，用于去重",
            actions=[
                ActionSpec(
                    name="check_visited",
                    description="检查某视频是否已评论过",
                    parameters={
                        "video_id": ParamSpec(type="string", description="视频BV号"),
                    },
                    returns={"visited": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="mark_visited",
                    description="标记视频为已评论",
                    parameters={
                        "video_id": ParamSpec(type="string", description="视频BV号"),
                    },
                    returns={"added": "bool"},
                    side_effects=["modifies history"],
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_all_visited",
                    description="获取所有已评论的视频ID",
                    returns={"video_ids": "list[str]", "count": "int"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="clear_history",
                    description="清空历史记录",
                    returns={"cleared": "bool"},
                    side_effects=["clears history"],
                    estimated_duration="fast",
                    risk_level="moderate",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="data_processing",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)
        mgr = self._get_mgr()

        try:
            if action == "check_visited":
                visited = mgr.has(params["video_id"])
                return ActionResult(success=True, data={"visited": visited})

            if action == "mark_visited":
                mgr.add(params["video_id"])
                return ActionResult(success=True, data={"added": True})

            if action == "get_all_visited":
                ids = list(mgr.visited)
                return ActionResult(success=True, data={"video_ids": ids, "count": len(ids)})

            if action == "clear_history":
                mgr.visited.clear()
                mgr._save()
                return ActionResult(success=True, data={"cleared": True})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action in ("check_visited", "mark_visited") and not params.get("video_id"):
            return False, "video_id is required"
        return True, ""

    async def health_check(self) -> bool:
        return True
