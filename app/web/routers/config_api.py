from __future__ import annotations

import os
from typing import Any, Dict

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.config import ConfigValidator
from core.slot import get_config_path, ensure_slot_dir
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()


class ConfigUpdateBody(BaseModel):
    config: Dict[str, Any]


def _deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> None:
    """把 incoming 递归合并进 base，只更新 incoming 里有的键，避免部分提交覆盖整段配置。"""
    for k, v in incoming.items():
        if k not in base:
            base[k] = v
        elif isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _read_raw_config(path: str) -> Dict[str, Any]:
    """Read config and fill defaults without running required-field validation."""
    if not os.path.exists(path):
        ConfigValidator.load_config(path)
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return ConfigValidator.validate_and_fill_defaults(raw, strict=False)


@router.get("")
async def get_config(slot: str = Query("0", alias="slot")):
    try:
        ensure_slot_dir(slot)
        path = get_config_path(slot)
        config = _read_raw_config(path)
        if "ai" in config and config["ai"].get("api_key"):
            masked = config["ai"].get("api_key", "")
            if masked not in ("", "YOUR_API_KEY_HERE"):
                config["ai"]["api_key"] = "***"
        return config
    except Exception as e:
        raise HTTPException(500, str(e))


@router.put("")
async def update_config(body: ConfigUpdateBody, slot: str = Query("0", alias="slot")):
    try:
        ensure_slot_dir(slot)
        path = os.path.abspath(get_config_path(slot))
        existing = _read_raw_config(path)

        incoming = body.config
        if "ai" in incoming and incoming["ai"].get("api_key") == "***":
            incoming["ai"]["api_key"] = existing.get("ai", {}).get("api_key", "")

        # 深合并，避免控制台只传 { ai: { comment: { enabled: true } } } 时把 api_key 等整段覆盖掉
        _deep_merge(existing, incoming)
        validated = ConfigValidator.validate_and_fill_defaults(existing, strict=False)
        ConfigValidator.save_config(validated, path)
        logger.info(f"Config saved to {path}")
        return {"status": "ok", "path": path}
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        raise HTTPException(400, str(e))
