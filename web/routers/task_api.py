from __future__ import annotations

import asyncio
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

import main as backend_main
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

_task_state: Dict[str, Any] = {
    "comment": {"running": False, "thread": None, "videos": [], "status": "idle", "stats": {}},
    "warmup": {"running": False, "thread": None, "status": "idle", "stats": {}},
}
_state_lock = threading.Lock()


class TaskStartResponse(BaseModel):
    status: str
    message: str


def _video_callback(video_info: dict):
    with _state_lock:
        videos = _task_state["comment"]["videos"]
        if not any(v.get("bv") == video_info.get("bv") for v in videos):
            videos.append({**video_info, "status": "pending"})


def _status_callback(bv: str, status: str):
    with _state_lock:
        for v in _task_state["comment"]["videos"]:
            if v.get("bv") == bv:
                v["status"] = status
                break


def _run_comment_task():
    try:
        with _state_lock:
            _task_state["comment"]["status"] = "running"
        backend_main.main(
            video_callback=_video_callback,
            status_callback=_status_callback,
        )
        with _state_lock:
            _task_state["comment"]["status"] = "completed"
    except Exception as e:
        logger.error(f"Comment task error: {e}")
        with _state_lock:
            _task_state["comment"]["status"] = f"error: {e}"
    finally:
        with _state_lock:
            _task_state["comment"]["running"] = False


def _warmup_status_callback(info: dict):
    with _state_lock:
        _task_state["warmup"]["stats"] = info


def _run_warmup_task():
    try:
        with _state_lock:
            _task_state["warmup"]["status"] = "running"
        backend_main.run_warmup()
        with _state_lock:
            _task_state["warmup"]["status"] = "completed"
    except Exception as e:
        logger.error(f"Warmup task error: {e}")
        with _state_lock:
            _task_state["warmup"]["status"] = f"error: {e}"
    finally:
        with _state_lock:
            _task_state["warmup"]["running"] = False


@router.post("/comment/start", response_model=TaskStartResponse)
async def start_comment():
    with _state_lock:
        if _task_state["comment"]["running"]:
            return TaskStartResponse(status="error", message="Comment task already running")
        _task_state["comment"]["running"] = True
        _task_state["comment"]["videos"] = []
        _task_state["comment"]["status"] = "starting"
        _task_state["comment"]["stats"] = {}

    t = threading.Thread(target=_run_comment_task, daemon=True)
    _task_state["comment"]["thread"] = t
    t.start()
    return TaskStartResponse(status="ok", message="Comment task started")


@router.post("/comment/stop", response_model=TaskStartResponse)
async def stop_comment():
    backend_main.stop_task()
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/comment/status")
async def comment_status():
    with _state_lock:
        return {
            "running": _task_state["comment"]["running"],
            "status": _task_state["comment"]["status"],
            "video_count": len(_task_state["comment"]["videos"]),
            "videos": _task_state["comment"]["videos"][-50:],
        }


@router.post("/warmup/start", response_model=TaskStartResponse)
async def start_warmup():
    with _state_lock:
        if _task_state["warmup"]["running"]:
            return TaskStartResponse(status="error", message="Warmup task already running")
        _task_state["warmup"]["running"] = True
        _task_state["warmup"]["status"] = "starting"
        _task_state["warmup"]["stats"] = {}

    t = threading.Thread(target=_run_warmup_task, daemon=True)
    _task_state["warmup"]["thread"] = t
    t.start()
    return TaskStartResponse(status="ok", message="Warmup task started")


@router.post("/warmup/stop", response_model=TaskStartResponse)
async def stop_warmup():
    backend_main.stop_task()
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/warmup/status")
async def warmup_status():
    with _state_lock:
        return {
            "running": _task_state["warmup"]["running"],
            "status": _task_state["warmup"]["status"],
            "stats": _task_state["warmup"]["stats"],
        }
