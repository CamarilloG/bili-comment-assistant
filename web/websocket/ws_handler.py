from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from utils.logger import get_logger

logger = get_logger()

router = APIRouter()


@router.websocket("/ws/session/{session_id}")
async def ws_session(websocket: WebSocket, session_id: str):
    from web.app import event_bus

    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    event_bus.register_ws(session_id, queue)
    logger.info(f"WebSocket connected for session {session_id}")

    try:
        # Run two concurrent tasks: sending events & receiving heartbeats
        send_task = asyncio.create_task(_send_loop(websocket, queue))
        recv_task = asyncio.create_task(_recv_loop(websocket))

        done, pending = await asyncio.wait(
            {send_task, recv_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        event_bus.unregister_ws(session_id, queue)
        logger.info(f"WebSocket disconnected for session {session_id}")


async def _send_loop(websocket: WebSocket, queue: asyncio.Queue) -> None:
    while True:
        event = await queue.get()
        try:
            payload = event.model_dump(mode="json")
            # Ensure datetime is serializable
            payload["timestamp"] = str(payload.get("timestamp", ""))
            await websocket.send_json(payload)
        except Exception:
            break


async def _recv_loop(websocket: WebSocket) -> None:
    """Receive messages (heartbeats) to detect disconnection."""
    while True:
        try:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
        except WebSocketDisconnect:
            break
        except Exception:
            break
