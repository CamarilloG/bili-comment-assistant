"""QQ bot adapter — stub implementation.

Designed to work with go-cqhttp / OpenShamrock style HTTP/WebSocket APIs.
"""

from __future__ import annotations

from bots.base import IBotAdapter
from utils.logger import get_logger

logger = get_logger()


class QQBotAdapter(IBotAdapter):
    """Adapter for QQ bot frameworks (go-cqhttp / OpenShamrock / Lagrange).

    Requires:
        - api_url: e.g. http://localhost:5700
        - access_token: optional auth token
        - target_group: default group ID for notifications
    """

    def __init__(self, config: dict):
        self._config = config
        self._api_url: str = config.get("api_url", "http://localhost:5700")
        self._access_token: str = config.get("access_token", "")
        self._target_group: str = config.get("target_group", "")
        self._enabled: bool = config.get("enabled", False)
        self._message_callback = None

    async def start(self) -> None:
        if not self._enabled:
            logger.info("[QQBot] Adapter disabled, skipping start")
            return
        logger.info(f"[QQBot] Adapter started (stub) — API: {self._api_url}")

    async def stop(self) -> None:
        logger.info("[QQBot] Adapter stopped (stub)")

    async def send_message(self, target: str, content: str) -> bool:
        # TODO: POST to {api_url}/send_group_msg or /send_private_msg
        logger.info(f"[QQBot] send_message stub -> target={target}, content={content[:50]}")
        raise NotImplementedError("QQBot send_message not yet implemented")

    async def send_image(self, target: str, image_path: str) -> bool:
        # TODO: Send CQ code image or use /send_group_msg with image segment
        logger.info(f"[QQBot] send_image stub -> target={target}, path={image_path}")
        raise NotImplementedError("QQBot send_image not yet implemented")
