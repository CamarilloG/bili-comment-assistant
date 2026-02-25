"""Enterprise WeChat (WeCom) bot adapter — stub implementation."""

from __future__ import annotations

from bots.base import IBotAdapter
from utils.logger import get_logger

logger = get_logger()


class WeComBotAdapter(IBotAdapter):
    """Adapter for Enterprise WeChat group bot via Webhook API.

    Requires:
        - webhook_url: https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=XXX
        - (optional) callback settings for receiving messages
    """

    def __init__(self, config: dict):
        self._config = config
        self._webhook_url: str = config.get("webhook_url", "")
        self._enabled: bool = config.get("enabled", False)
        self._message_callback = None

    async def start(self) -> None:
        if not self._enabled:
            logger.info("[WeCom] Adapter disabled, skipping start")
            return
        if not self._webhook_url:
            raise ValueError("WeCom webhook_url is required")
        logger.info("[WeCom] Adapter started (stub)")

    async def stop(self) -> None:
        logger.info("[WeCom] Adapter stopped (stub)")

    async def send_message(self, target: str, content: str) -> bool:
        # TODO: POST to self._webhook_url with {"msgtype": "text", "text": {"content": content}}
        logger.info(f"[WeCom] send_message stub -> target={target}, content={content[:50]}")
        raise NotImplementedError("WeCom send_message not yet implemented")

    async def send_image(self, target: str, image_path: str) -> bool:
        # TODO: Upload image via WeCom media API, then send image message
        logger.info(f"[WeCom] send_image stub -> target={target}, path={image_path}")
        raise NotImplementedError("WeCom send_image not yet implemented")
