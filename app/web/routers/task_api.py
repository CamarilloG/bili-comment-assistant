from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

# 修复打包后的导入问题：使用相对导入
try:
    import main as backend_main
except ModuleNotFoundError:
    # 打包环境中使用绝对导入
    import sys
    import os
    # 确保 app 目录在路径中
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    import main as backend_main

from core.slot import get_workdir
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

# 按槽位：_task_state[slot_id] = {"comment": {...}, "warmup": {...}}
_task_state: Dict[str, Dict[str, Any]] = {}
_state_lock = threading.Lock()


def _default_slot_state() -> Dict[str, Any]:
    return {
        "comment": {"running": False, "thread": None, "videos": [], "status": "idle", "stats": {}},
        "warmup": {"running": False, "thread": None, "status": "idle", "stats": {}},
    }


def _get_slot_state(slot_id: str) -> Dict[str, Any]:
    with _state_lock:
        if slot_id not in _task_state:
            _task_state[slot_id] = _default_slot_state()
        return _task_state[slot_id]


class TaskStartResponse(BaseModel):
    status: str
    message: str


class CommentStartRequest(BaseModel):
    """前端启动评论任务时可指定模式：comment（普通）或 ai。"""
    mode: str = "comment"


def _make_video_callback(slot_id: str):
    def _cb(video_info: dict):
        with _state_lock:
            if slot_id not in _task_state:
                _task_state[slot_id] = _default_slot_state()
            state = _task_state[slot_id]
            videos = state["comment"]["videos"]
            if not any(v.get("bv") == video_info.get("bv") for v in videos):
                videos.append({**video_info, "status": "pending"})
    return _cb


def _make_status_callback(slot_id: str):
    def _cb(bv: str, status: str, comment_content: Optional[str] = None, comment_type: Optional[str] = None):
        with _state_lock:
            if slot_id not in _task_state:
                _task_state[slot_id] = _default_slot_state()
            state = _task_state[slot_id]
            state["comment"]["status"] = status
            for v in state["comment"]["videos"]:
                if v.get("bv") == bv:
                    v["status"] = status
                    if comment_content is not None:
                        v["comment_content"] = comment_content
                    if comment_type is not None:
                        v["comment_type"] = comment_type
                    break
    return _cb


def _run_comment_task(slot_id: str, mode: str = "comment"):
    # 不在锁内调用，避免阻塞
    with _state_lock:
        if slot_id not in _task_state:
            _task_state[slot_id] = _default_slot_state()
        state = _task_state[slot_id]
    workdir = get_workdir(slot_id)
    logger.info(f"[任务启动] 开始评论任务 - slot_id={slot_id}, mode={mode}, workdir={workdir}")
    try:
        with _state_lock:
            state["comment"]["status"] = "running"
        logger.info(f"[任务启动] 调用 backend_main.main()")
        backend_main.main(
            video_callback=_make_video_callback(slot_id),
            status_callback=_make_status_callback(slot_id),
            workdir=workdir,
            slot_id=slot_id,
            mode=mode,
        )
        logger.info(f"[任务启动] backend_main.main() 执行完成")
        with _state_lock:
            state["comment"]["status"] = "completed"
    except Exception as e:
        logger.error(f"Comment task error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        with _state_lock:
            state["comment"]["status"] = f"error: {e}"
    finally:
        with _state_lock:
            state["comment"]["running"] = False
        logger.info(f"[任务启动] 任务结束 - slot_id={slot_id}")


def _make_warmup_status_callback(slot_id: str):
    def _cb(title: str, watched_count: int, minutes: float, like_count: int, comment_count: int):
        with _state_lock:
            if slot_id not in _task_state:
                _task_state[slot_id] = _default_slot_state()
            state = _task_state[slot_id]
            state["warmup"]["stats"] = {
                "title": title,
                "watched_count": watched_count,
                "minutes": minutes,
                "like_count": like_count,
                "comment_count": comment_count,
            }
    return _cb


def _run_warmup_task(slot_id: str):
    # 不在锁内调用，避免阻塞
    with _state_lock:
        if slot_id not in _task_state:
            _task_state[slot_id] = _default_slot_state()
        state = _task_state[slot_id]
    workdir = get_workdir(slot_id)
    try:
        with _state_lock:
            state["warmup"]["status"] = "running"
        backend_main.run_warmup(
            status_callback=_make_warmup_status_callback(slot_id),
            workdir=workdir,
            slot_id=slot_id,
        )
        with _state_lock:
            state["warmup"]["status"] = "completed"
    except Exception as e:
        logger.error(f"Warmup task error: {e}")
        with _state_lock:
            state["warmup"]["status"] = f"error: {e}"
    finally:
        with _state_lock:
            state["warmup"]["running"] = False


@router.post("/comment/start", response_model=TaskStartResponse)
async def start_comment(
    payload: CommentStartRequest | None = None,
    slot: str = Query("0", alias="slot"),
):
    try:
        logger.info(f"[API调用] /comment/start 被调用 - slot={slot}, payload={payload}")
        mode = (payload.mode if payload and payload.mode in ("comment", "ai") else "comment")
        logger.info(f"[API调用] mode={mode}")
        with _state_lock:
            # 直接访问 _task_state，不要调用 _get_slot_state（会导致死锁）
            if slot not in _task_state:
                _task_state[slot] = _default_slot_state()
            state = _task_state[slot]
            logger.info(f"[API调用] 获取状态 - running={state['comment']['running']}")
            if state["comment"]["running"]:
                logger.warning(f"[API调用] 任务已在运行")
                return TaskStartResponse(status="error", message="Comment task already running")
            state["comment"]["running"] = True
            state["comment"]["videos"] = []
            state["comment"]["status"] = "starting"
            state["comment"]["stats"] = {}

            t = threading.Thread(target=_run_comment_task, args=(slot, mode), daemon=True)
            state["comment"]["thread"] = t
            logger.info(f"[API调用] 准备启动线程 - thread={t}")
            t.start()
            logger.info(f"[API调用] 线程已启动 - thread.is_alive()={t.is_alive()}")

        logger.info(f"[API调用] 返回成功响应")
        return TaskStartResponse(status="ok", message="Comment task started")
    except Exception as e:
        logger.error(f"[API调用] 启动任务异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return TaskStartResponse(status="error", message=f"启动失败: {e}")


@router.post("/comment/stop", response_model=TaskStartResponse)
async def stop_comment(slot: str = Query("0", alias="slot")):
    backend_main.stop_task(slot)
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/comment/status")
async def comment_status(slot: str = Query("0", alias="slot")):
    with _state_lock:
        if slot not in _task_state:
            _task_state[slot] = _default_slot_state()
        state = _task_state[slot]
        recent = state["comment"]["videos"][-50:]
        return {
            "running": state["comment"]["running"],
            "status": state["comment"]["status"],
            "video_count": len(state["comment"]["videos"]),
            "videos": list(reversed(recent)),
        }


@router.post("/warmup/start", response_model=TaskStartResponse)
async def start_warmup(slot: str = Query("0", alias="slot")):
    with _state_lock:
        if slot not in _task_state:
            _task_state[slot] = _default_slot_state()
        state = _task_state[slot]
        if state["warmup"]["running"]:
            return TaskStartResponse(status="error", message="Warmup task already running")
        state["warmup"]["running"] = True
        state["warmup"]["status"] = "starting"
        state["warmup"]["stats"] = {}

        t = threading.Thread(target=_run_warmup_task, args=(slot,), daemon=True)
        state["warmup"]["thread"] = t
        t.start()

    return TaskStartResponse(status="ok", message="Warmup task started")


@router.post("/warmup/stop", response_model=TaskStartResponse)
async def stop_warmup(slot: str = Query("0", alias="slot")):
    backend_main.stop_task(slot)
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/warmup/status")
async def warmup_status(slot: str = Query("0", alias="slot")):
    with _state_lock:
        if slot not in _task_state:
            _task_state[slot] = _default_slot_state()
        state = _task_state[slot]
        return {
            "running": state["warmup"]["running"],
            "status": state["warmup"]["status"],
            "stats": state["warmup"]["stats"],
        }
