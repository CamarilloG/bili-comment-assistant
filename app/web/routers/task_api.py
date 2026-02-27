from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

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
        state = _get_slot_state(slot_id)
        with _state_lock:
            videos = state["comment"]["videos"]
            if not any(v.get("bv") == video_info.get("bv") for v in videos):
                videos.append({**video_info, "status": "pending"})
    return _cb


def _make_status_callback(slot_id: str):
    def _cb(bv: str, status: str, comment_content: Optional[str] = None, comment_type: Optional[str] = None):
        state = _get_slot_state(slot_id)
        with _state_lock:
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
    state = _get_slot_state(slot_id)
    workdir = get_workdir(slot_id)
    try:
        with _state_lock:
            state["comment"]["status"] = "running"
        backend_main.main(
            video_callback=_make_video_callback(slot_id),
            status_callback=_make_status_callback(slot_id),
            workdir=workdir,
            slot_id=slot_id,
            mode=mode,
        )
        with _state_lock:
            state["comment"]["status"] = "completed"
    except Exception as e:
        logger.error(f"Comment task error: {e}")
        with _state_lock:
            state["comment"]["status"] = f"error: {e}"
    finally:
        with _state_lock:
            state["comment"]["running"] = False


def _make_warmup_status_callback(slot_id: str):
    def _cb(title: str, watched_count: int, minutes: float, like_count: int, comment_count: int):
        state = _get_slot_state(slot_id)
        with _state_lock:
            state["warmup"]["stats"] = {
                "title": title,
                "watched_count": watched_count,
                "minutes": minutes,
                "like_count": like_count,
                "comment_count": comment_count,
            }
    return _cb


def _run_warmup_task(slot_id: str):
    state = _get_slot_state(slot_id)
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
    state = _get_slot_state(slot)
    mode = (payload.mode if payload and payload.mode in ("comment", "ai") else "comment")
    # #region agent log
    try:
        import json, os, time as _t
        log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "debug-829736.log"))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "sessionId": "829736",
                "timestamp": int(_t.time() * 1000),
                "location": "task_api.py:start_comment",
                "message": "start_comment called",
                "hypothesisId": "H1",
                "data": {"slot": slot, "mode": mode},
            }) + "\n")
    except Exception:
        pass
    # #endregion
    with _state_lock:
        if state["comment"]["running"]:
            return TaskStartResponse(status="error", message="Comment task already running")
        state["comment"]["running"] = True
        state["comment"]["videos"] = []
        state["comment"]["status"] = "starting"
        state["comment"]["stats"] = {}

    t = threading.Thread(target=_run_comment_task, args=(slot, mode), daemon=True)
    with _state_lock:
        state["comment"]["thread"] = t
    t.start()
    return TaskStartResponse(status="ok", message="Comment task started")


@router.post("/comment/stop", response_model=TaskStartResponse)
async def stop_comment(slot: str = Query("0", alias="slot")):
    backend_main.stop_task(slot)
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/comment/status")
async def comment_status(slot: str = Query("0", alias="slot")):
    state = _get_slot_state(slot)
    with _state_lock:
        recent = state["comment"]["videos"][-50:]
        return {
            "running": state["comment"]["running"],
            "status": state["comment"]["status"],
            "video_count": len(state["comment"]["videos"]),
            "videos": list(reversed(recent)),
        }


@router.post("/warmup/start", response_model=TaskStartResponse)
async def start_warmup(slot: str = Query("0", alias="slot")):
    state = _get_slot_state(slot)
    with _state_lock:
        if state["warmup"]["running"]:
            return TaskStartResponse(status="error", message="Warmup task already running")
        state["warmup"]["running"] = True
        state["warmup"]["status"] = "starting"
        state["warmup"]["stats"] = {}

    t = threading.Thread(target=_run_warmup_task, args=(slot,), daemon=True)
    with _state_lock:
        state["warmup"]["thread"] = t
    t.start()
    return TaskStartResponse(status="ok", message="Warmup task started")


@router.post("/warmup/stop", response_model=TaskStartResponse)
async def stop_warmup(slot: str = Query("0", alias="slot")):
    backend_main.stop_task(slot)
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/warmup/status")
async def warmup_status(slot: str = Query("0", alias="slot")):
    state = _get_slot_state(slot)
    with _state_lock:
        return {
            "running": state["warmup"]["running"],
            "status": state["warmup"]["status"],
            "stats": state["warmup"]["stats"],
        }
