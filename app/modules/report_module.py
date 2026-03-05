from __future__ import annotations

import csv
import io
import os
from datetime import datetime
from typing import Any, Dict, List

from modules.base import (
    ActionResult,
    ActionSpec,
    ExecutionContext,
    IModule,
    ModuleCapability,
    ParamSpec,
)


class ReportModule(IModule):
    """Session-level result logging and CSV export.

    注意：export_csv 的 path 参数默认为相对路径 "comment_log.csv"。
    在多实例环境下，调用者应使用 slot.get_comment_log_path(slot_id) 获取绝对路径。
    """

    def __init__(self) -> None:
        self._records: Dict[str, List[Dict[str, Any]]] = {}  # session_id -> records

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="report",
            description="报告模块，记录评论结果并生成会话报告/CSV导出",
            actions=[
                ActionSpec(
                    name="log_result",
                    description="记录一条评论结果",
                    parameters={
                        "video_info": ParamSpec(type="dict", description="视频信息"),
                        "status": ParamSpec(type="string", description="结果状态"),
                        "comment": ParamSpec(type="string", description="评论文本"),
                        "source": ParamSpec(type="string", description="来源", required=False, default="Template"),
                    },
                    returns={"logged": "bool"},
                    side_effects=["appends to report"],
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_session_report",
                    description="获取指定会话的汇总报告",
                    parameters={
                        "session_id": ParamSpec(type="string", description="会话ID"),
                    },
                    returns={"summary": "dict", "details": "list"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="export_csv",
                    description="将会话报告导出为CSV文件",
                    parameters={
                        "session_id": ParamSpec(type="string", description="会话ID"),
                        "path": ParamSpec(type="string", description="CSV路径", required=False, default="comment_log.csv"),
                    },
                    returns={"exported": "bool", "path": "str"},
                    side_effects=["writes CSV file"],
                    estimated_duration="fast",
                    risk_level="safe",
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
        sid = params.get("session_id") or context.session_id or "default"

        try:
            if action == "log_result":
                video_info = params.get("video_info") if isinstance(params.get("video_info"), dict) else {}
                rec = {
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "bv": video_info.get("bv", ""),
                    "title": video_info.get("title", ""),
                    "author": video_info.get("author", ""),
                    "status": params.get("status") or "",
                    "comment": params.get("comment") or "",
                    "source": params.get("source") or "Template",
                }
                self._records.setdefault(sid, []).append(rec)
                return ActionResult(success=True, data={"logged": True})

            if action == "get_session_report":
                records = self._records.get(sid, [])
                total = len(records)
                success = sum(1 for r in records if r["status"] == "成功")
                failed = sum(1 for r in records if r["status"] == "失败")
                captcha = sum(1 for r in records if "验证码" in r["status"])
                return ActionResult(
                    success=True,
                    data={
                        "summary": {
                            "total": total,
                            "success": success,
                            "failed": failed,
                            "captcha": captcha,
                        },
                        "details": records,
                    },
                )

            if action == "export_csv":
                records = self._records.get(sid, [])
                path = params.get("path", "comment_log.csv")
                file_exists = os.path.isfile(path)
                with open(path, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["Time", "BV", "Title", "Author", "Status", "Comment", "Source"])
                    for rec in records:
                        writer.writerow([
                            rec["time"], rec["bv"], rec["title"],
                            rec["author"], rec["status"], rec["comment"], rec["source"],
                        ])
                return ActionResult(success=True, data={"exported": True, "path": path})

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "log_result" and not params.get("video_info"):
            return False, "video_info is required"
        if action in ("get_session_report", "export_csv") and not params.get("session_id"):
            return False, "session_id is required"
        return True, ""

    async def health_check(self) -> bool:
        return True
