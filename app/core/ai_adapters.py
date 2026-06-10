"""按 api_type 创建 OpenAI 兼容客户端，openai / openrouter 均使用同一接口。"""
from __future__ import annotations

from typing import Any

from openai import OpenAI


def create_client(
    base_url: str,
    api_key: str,
    timeout: int = 30,
    api_type: str = "openai",
) -> OpenAI:
    """根据 api_type 创建客户端。目前 openai 与 openrouter 均使用 OpenAI 兼容接口。"""
    if api_type == "openrouter":
        base_url = base_url or "https://openrouter.ai/api/v1"
    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        timeout=timeout,
    )
