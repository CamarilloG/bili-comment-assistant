from __future__ import annotations

import asyncio
import json
import queue
import threading

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger, sanitize_log

logger = get_logger()
router = APIRouter()

_log_subscribers: list[queue.Queue] = []
_log_lock = threading.Lock()


def broadcast_log(message: str):
    with _log_lock:
        dead = []
        for q in _log_subscribers:
            try:
                q.put_nowait(message)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _log_subscribers.remove(q)


def _install_log_hook():
    """Install loguru sink that broadcasts JSON to WebSocket for 按字段着色."""
    from loguru import logger as loguru_logger

    def _json_format(record):
        # sanitize 在 filter 中已应用，此处 record 已是脱敏后的 message
        # 返回的字符串会被 loguru 再次 format_map(record)，故需转义 { } 避免 KeyError
        t = record["time"]
        time_str = t.strftime("%H:%M:%S") if hasattr(t, "strftime") else str(t)
        level_name = record["level"].name if hasattr(record["level"], "name") else str(record["level"])
        s = json.dumps(
            {"time": time_str, "level": level_name, "message": record["message"]},
            ensure_ascii=False,
        )
        return s.replace("{", "{{").replace("}", "}}")

    def _ws_sink(message):
        broadcast_log(str(message).rstrip())

    loguru_logger.add(
        _ws_sink,
        format=_json_format,
        filter=sanitize_log,
        level="INFO",
    )


_install_log_hook()


@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    await websocket.accept()
    q: queue.Queue = queue.Queue(maxsize=512)
    with _log_lock:
        _log_subscribers.append(q)

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
            if q in _log_subscribers:
                _log_subscribers.remove(q)
