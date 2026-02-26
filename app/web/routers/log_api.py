from __future__ import annotations

import asyncio
import queue
import threading
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger, sanitize_log, slot_id_ctx

logger = get_logger()
router = APIRouter()

# 按槽位：slot_id -> list of queues，仅该槽位的订阅者收到该槽位的运行日志
_log_subscribers: Dict[str, List[queue.Queue]] = {}
_log_lock = threading.Lock()


def broadcast_log(message: str, slot_id: str | None = None):
    """推送一条运行日志。slot_id 为 None 时从当前上下文取，取不到则视为 "0"。"""
    if slot_id is None:
        try:
            slot_id = slot_id_ctx.get() or "0"
        except LookupError:
            slot_id = "0"
    with _log_lock:
        queues = _log_subscribers.get(slot_id, [])
        dead = []
        for q in queues:
            try:
                q.put_nowait(message)
            except queue.Full:
                dead.append(q)
        for q in dead:
            queues.remove(q)


def _install_log_hook():
    """Install loguru sink that broadcasts to WebSocket for 按字段着色.
    使用 Tab 分隔 time/level/message；按 slot_id_ctx 将日志投递到对应槽位订阅者。
    """
    from loguru import logger as loguru_logger

    def _tsv_format(record):
        t = record["time"]
        time_str = t.strftime("%H:%M:%S") if hasattr(t, "strftime") else str(t)
        level_name = record["level"].name if hasattr(record["level"], "name") else str(record["level"])
        msg = record["message"].replace("\t", " ") if record.get("message") else ""
        return f"{time_str}\t{level_name}\t{msg}"

    def _ws_sink(message):
        broadcast_log(str(message).rstrip(), slot_id=None)

    loguru_logger.add(
        _ws_sink,
        format=_tsv_format,
        filter=sanitize_log,
        level="INFO",
    )


_install_log_hook()


def _get_slot_from_scope(scope: dict) -> str:
    qs = (scope.get("query_string") or "").decode() if isinstance(scope.get("query_string"), bytes) else (scope.get("query_string") or "")
    for part in qs.split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k.strip().lower() == "slot":
                return (v.strip() or "0") or "0"
    return "0"


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    slot = _get_slot_from_scope(websocket.scope)
    q: queue.Queue = queue.Queue(maxsize=512)
    with _log_lock:
        _log_subscribers.setdefault(slot, []).append(q)

    try:
        while True:
            try:
                msg = await asyncio.get_event_loop().run_in_executor(None, q.get, True, 1.0)
                await websocket.send_text(msg)
            except queue.Empty:
                continue
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        with _log_lock:
            lst = _log_subscribers.get(slot, [])
            if q in lst:
                lst.remove(q)
