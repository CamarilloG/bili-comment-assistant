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


def _deep_merge(base: Dict, update: Dict) -> Dict:
    """深度合并两个字典，update 中的值会覆盖 base 中的值。"""
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigUpdateBody(BaseModel):
    config: Dict[str, Any]


def _read_raw_config(path: str) -> Dict[str, Any]:
    """Read config and fill defaults without running required-field validation."""
    import os
    if not os.path.exists(path):
        ConfigValidator.load_config(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return ConfigValidator.validate_and_fill_defaults(raw, strict=False)


@router.get("")
async def get_config():
    try:
        import os
        config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(config_dir, "config.yaml")

        config = _read_raw_config(config_path)
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
        import os
        config_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(config_dir, "config.yaml")
        logger.info(f"Updating config, path: {config_path}")

        existing = _read_raw_config(config_path)

        incoming = body.config
        if "ai" in incoming and incoming["ai"].get("api_key") == "***":
            incoming["ai"]["api_key"] = existing.get("ai", {}).get("api_key", "")

        merged = _deep_merge(existing, incoming)
        validated = ConfigValidator.validate_and_fill_defaults(merged, strict=False)
        ConfigValidator.save_config(validated, config_path)

        logger.info(f"Config saved, ai.enabled: {validated.get('ai', {}).get('enabled')}")
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(400, str(e))
