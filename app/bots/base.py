"""Abstract base class for all bot adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class IBotAdapter(ABC):
    """Uniform interface that every bot platform adapter must implement."""

    @abstractmethod
    async def start(self) -> None:
        """Initialize connection / webhook listener."""

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully tear down connection."""

    @abstractmethod
    async def send_message(self, target: str, content: str) -> bool:
        """Send a text message to *target* (user/group/channel id)."""

    @abstractmethod
    async def send_image(self, target: str, image_path: str) -> bool:
        """Send an image file to *target*."""

    def on_message(self, callback: Callable[[str, str, dict], Any]) -> None:
        """Register a callback invoked on incoming messages.

        callback(source_id, text, raw_payload)
        """
        self._message_callback = callback

    @property
    def name(self) -> str:
        return self.__class__.__name__
