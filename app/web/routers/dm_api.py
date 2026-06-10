"""Independent DM task router — parallel to comment and warmup task routes."""

from __future__ import annotations

import threading
from typing import Any, Dict

from fastapi import APIRouter, Query
from pydantic import BaseModel

try:
    from core.dm_flow import run_dm, stop_dm_task
except ModuleNotFoundError:
    import sys, os
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if app_dir not in sys.path:
        sys.path.insert(0, app_dir)
    from core.dm_flow import run_dm, stop_dm_task

from core.slot import get_workdir
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

_dm_state: Dict[str, Dict[str, Any]] = {}
_state_lock = threading.Lock()


def _default_dm_state() -> Dict[str, Any]:
    return {
        "running": False,
        "thread": None,
        "status": "idle",
        "stats": {},
    }


def _get_dm_state(slot_id: str) -> Dict[str, Any]:
    with _state_lock:
        if slot_id not in _dm_state:
            _dm_state[slot_id] = _default_dm_state()
        return _dm_state[slot_id]


class TaskStartResponse(BaseModel):
    status: str
    message: str


def _make_dm_status_callback(slot_id: str):
    def _cb(status: str, stats: dict):
        with _state_lock:
            if slot_id not in _dm_state:
                _dm_state[slot_id] = _default_dm_state()
            state = _dm_state[slot_id]
            state["status"] = status
            state["stats"] = stats
    return _cb


def _run_dm_task(slot_id: str):
    with _state_lock:
        if slot_id not in _dm_state:
            _dm_state[slot_id] = _default_dm_state()
        state = _dm_state[slot_id]
    workdir = get_workdir(slot_id)
    try:
        with _state_lock:
            state["status"] = "running"
        run_dm(
            status_callback=_make_dm_status_callback(slot_id),
            workdir=workdir,
            slot_id=slot_id,
        )
        with _state_lock:
            state["status"] = "completed"
    except Exception as e:
        logger.error(f"DM task error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        with _state_lock:
            state["status"] = f"error: {e}"
    finally:
        with _state_lock:
            state["running"] = False


@router.post("/start", response_model=TaskStartResponse)
async def start_dm(slot: str = Query("0", alias="slot")):
    with _state_lock:
        if slot not in _dm_state:
            _dm_state[slot] = _default_dm_state()
        state = _dm_state[slot]
        if state["running"]:
            return TaskStartResponse(status="error", message="DM task already running")
        state["running"] = True
        state["status"] = "starting"
        state["stats"] = {}

        t = threading.Thread(target=_run_dm_task, args=(slot,), daemon=True)
        state["thread"] = t
        t.start()

    return TaskStartResponse(status="ok", message="DM task started")


@router.post("/stop", response_model=TaskStartResponse)
async def stop_dm(slot: str = Query("0", alias="slot")):
    stop_dm_task(slot)
    return TaskStartResponse(status="ok", message="Stop signal sent")


@router.get("/status")
async def dm_status(slot: str = Query("0", alias="slot")):
    with _state_lock:
        if slot not in _dm_state:
            _dm_state[slot] = _default_dm_state()
        state = _dm_state[slot]
        return {
            "running": state["running"],
            "status": state["status"],
            "stats": state["stats"],
        }
