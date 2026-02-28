"""模型注册表：从项目固定配置加载模型列表，供运行时按 model_id 获取配置。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

_CONFIG_DIR = Path(__file__).resolve().parent
MODELS_CONFIG_PATH = _CONFIG_DIR / "models_config.yaml"

_models_cache: Optional[List[Dict[str, Any]]] = None


def _load_models() -> List[Dict[str, Any]]:
    global _models_cache
    if _models_cache is not None:
        return _models_cache
    if not MODELS_CONFIG_PATH.exists():
        _models_cache = []
        return _models_cache
    with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    raw = data.get("models") if isinstance(data, dict) else []
    _models_cache = list(raw) if isinstance(raw, list) else []
    return _models_cache


def _resolve_api_key(model_id: str, api_key: str) -> str:
    """优先从环境变量读取 api_key，键名 MODEL_<ID大写下划线>_API_KEY。"""
    env_key = "MODEL_" + model_id.upper().replace("-", "_") + "_API_KEY"
    return os.environ.get(env_key, "").strip() or (api_key or "").strip()


def list_models(include_secrets: bool = False) -> List[Dict[str, Any]]:
    """返回所有模型配置。默认不包含 api_key（用于前端）；include_secrets=True 时包含。"""
    models = _load_models()
    out = []
    for m in models:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        row = {
            "id": str(m["id"]),
            "model_name": str(m.get("model_name", m["id"])),
            "model": str(m.get("model", "")),
            "base_url": str(m.get("base_url", "")),
            "api_type": str(m.get("api_type", "openai")),
            "price": str(m.get("price", "")),
        }
        if include_secrets:
            row["api_key"] = _resolve_api_key(row["id"], m.get("api_key") or "")
        else:
            row["api_key"] = ""
        out.append(row)
    return out


def get_model_by_id(model_id: str) -> Optional[Dict[str, Any]]:
    """按 id 获取单条模型配置，api_key 已做环境变量解析。"""
    if not model_id:
        return None
    models = _load_models()
    for m in models:
        if not isinstance(m, dict):
            continue
        if str(m.get("id", "")) == str(model_id):
            api_key = _resolve_api_key(str(m["id"]), m.get("api_key") or "")
            return {
                "id": str(m["id"]),
                "model_name": str(m.get("model_name", m["id"])),
                "model": str(m.get("model", "")),
                "base_url": str(m.get("base_url", "")),
                "api_key": api_key,
                "api_type": str(m.get("api_type", "openai")),
                "price": str(m.get("price", "")),
            }
    return None


def get_default_model_id() -> str:
    """返回默认模型 id（列表第一个）。"""
    models = list_models(include_secrets=False)
    return models[0]["id"] if models else "deepseek_chat"
