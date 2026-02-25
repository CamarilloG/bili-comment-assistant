"""Bot command handler — parses incoming messages and dispatches actions.

Supported commands (planned):
    /status  — Report current task status
    /start   — Start the comment task
    /stop    — Stop the running task
    /config  — Show or update config snippet
    /help    — List available commands
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from bots.base import IBotAdapter
from utils.logger import get_logger

logger = get_logger()

COMMANDS: Dict[str, str] = {
    "/status": "查看当前任务状态",
    "/start": "启动自动评论任务",
    "/stop": "停止当前任务",
    "/config": "查看/修改配置",
    "/help": "显示帮助信息",
}


class BotCommandHandler:
    """Receives raw text from any IBotAdapter, parses commands, dispatches actions."""

    def __init__(self):
        self._adapters: list[IBotAdapter] = []

    def register_adapter(self, adapter: IBotAdapter) -> None:
        adapter.on_message(self._on_message)
        self._adapters.append(adapter)
        logger.info(f"[CommandHandler] Registered adapter: {adapter.name}")

    def _on_message(self, source_id: str, text: str, raw: dict) -> None:
        text = text.strip()
        if not text.startswith("/"):
            return

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handler = {
            "/status": self._cmd_status,
            "/start": self._cmd_start,
            "/stop": self._cmd_stop,
            "/config": self._cmd_config,
            "/help": self._cmd_help,
        }.get(cmd)

        if handler:
            logger.info(f"[CommandHandler] {cmd} from {source_id}")
            handler(source_id, args)
        else:
            logger.debug(f"[CommandHandler] Unknown command: {cmd}")

    def _cmd_status(self, source_id: str, args: str) -> None:
        # TODO: Query task state and reply via adapter
        pass

    def _cmd_start(self, source_id: str, args: str) -> None:
        # TODO: Trigger comment task start
        pass

    def _cmd_stop(self, source_id: str, args: str) -> None:
        # TODO: Trigger task stop
        pass

    def _cmd_config(self, source_id: str, args: str) -> None:
        # TODO: Read/update config and reply
        pass

    def _cmd_help(self, source_id: str, args: str) -> None:
        # TODO: Reply with COMMANDS listing
        pass
