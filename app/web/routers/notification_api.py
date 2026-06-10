"""通知 API 路由"""
from __future__ import annotations

import asyncio
import queue
import threading
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

# 全局通知订阅者（所有实例的通知都会推送给所有订阅者）
_notification_subscribers: List[queue.Queue] = []
_notification_lock = threading.Lock()


def broadcast_notification(notification_data: dict):
    """广播通知到所有 WebSocket 订阅者"""
    with _notification_lock:
        dead = []
        for q in _notification_subscribers:
            try:
                q.put_nowait(notification_data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _notification_subscribers.remove(q)


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    """WebSocket 端点：接收全局通知"""
    await websocket.accept()
    q: queue.Queue = queue.Queue(maxsize=128)

    with _notification_lock:
        _notification_subscribers.append(q)

    logger.debug("Notification WebSocket connected")

    try:
        while True:
            try:
                # 从队列获取通知
                notification = await asyncio.get_event_loop().run_in_executor(
                    None, q.get, True, 1.0
                )
                # 发送 JSON 格式的通知
                await websocket.send_json(notification)
            except queue.Empty:
                continue
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Notification WebSocket error: {e}")
    finally:
        with _notification_lock:
            if q in _notification_subscribers:
                _notification_subscribers.remove(q)
        logger.debug("Notification WebSocket disconnected")
