from __future__ import annotations

import os
from typing import Any, Dict

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import ConfigValidator
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()


class ConfigUpdateBody(BaseModel):
    config: Dict[str, Any]


def _read_raw_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Read config and fill defaults without running required-field validation."""
    if not os.path.exists(path):
        ConfigValidator.load_config(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return ConfigValidator.validate_and_fill_defaults(raw, strict=False)


@router.get("")
async def get_config():
    try:
        config = _read_raw_config()
        if "ai" in config and config["ai"].get("api_key"):
            masked = config["ai"]["api_key"]
            if masked not in ("", "YOUR_API_KEY_HERE"):
                config["ai"]["api_key"] = "***"
        return config
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("")
async def update_config(body: ConfigUpdateBody):
    try:
        existing = _read_raw_config()

        incoming = body.config
        if "ai" in incoming and incoming["ai"].get("api_key") == "***":
            incoming["ai"]["api_key"] = existing.get("ai", {}).get("api_key", "")

        existing.update(incoming)
        validated = ConfigValidator.validate_and_fill_defaults(existing, strict=False)
        ConfigValidator.save_config(validated)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(400, str(e))
