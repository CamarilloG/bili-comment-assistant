"""模型注册表：从项目固定配置加载模型列表，供运行时按 model_id 获取配置。"""
from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# api_key 加密：配置里可写 enc:<base64>，此处解码后使用
def _decode_api_key(raw: str) -> str:
    """
    解密 API key
    - 如果是 enc: 开头，尝试使用 XOR + base64 解密
    - 如果 XOR 解密失败，降级到简单 base64 解码（兼容旧格式）
    - 否则原样返回（兼容明文）
    """
    raw = (raw or "").strip()
    if not raw or not raw.startswith("enc:"):
        return raw

    # 尝试新格式解密（XOR + base64）
    try:
        from utils.api_key_crypto import decode_api_key
        result = decode_api_key(raw)
        # 如果解密后仍然是 enc: 开头，说明解密失败，尝试旧格式
        if result.startswith("enc:"):
            raise ValueError("XOR decryption failed")
        return result
    except Exception:
        pass

    # 降级：尝试简单 base64 解码（兼容旧格式）
    try:
        return base64.b64decode(raw[4:].encode()).decode("utf-8")
    except Exception:
        return raw

_CONFIG_DIR = Path(__file__).resolve().parent
MODELS_CONFIG_PATH = _CONFIG_DIR / "models_config.yaml"

_models_cache: Optional[List[Dict[str, Any]]] = None
_cache_mtime: Optional[float] = None  # 缓存文件的修改时间


def _load_models() -> List[Dict[str, Any]]:
    """加载模型配置，支持文件修改后自动重载。"""
    global _models_cache, _cache_mtime

    # 检查文件是否存在
    if not MODELS_CONFIG_PATH.exists():
        _models_cache = []
        _cache_mtime = None
        return _models_cache

    # 获取文件修改时间
    current_mtime = MODELS_CONFIG_PATH.stat().st_mtime

    # 如果缓存存在且文件未修改，返回缓存
    if _models_cache is not None and _cache_mtime == current_mtime:
        return _models_cache

    # 重新加载配置
    with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    raw = data.get("models") if isinstance(data, dict) else []
    _models_cache = list(raw) if isinstance(raw, list) else []
    _cache_mtime = current_mtime

    return _models_cache


def reload_models() -> None:
    """强制重新加载模型配置（清除缓存）。"""
    global _models_cache, _cache_mtime
    _models_cache = None
    _cache_mtime = None


def _resolve_api_key(model_id: str, api_key: str) -> str:
    """优先从环境变量读取 api_key，键名 MODEL_<ID大写下划线>_API_KEY。

    将 model_id 中的所有非字母数字字符替换为下划线，以生成有效的环境变量名。
    例如：x-ai/grok-4.1-fast -> MODEL_X_AI_GROK_4_1_FAST_API_KEY
    """
    import re
    # 将所有非字母数字字符替换为下划线
    safe_id = re.sub(r'[^a-zA-Z0-9]', '_', model_id.upper())
    env_key = f"MODEL_{safe_id}_API_KEY"
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
            row["api_key"] = _resolve_api_key(row["id"], _decode_api_key(m.get("api_key") or ""))
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
            api_key = _resolve_api_key(str(m["id"]), _decode_api_key(m.get("api_key") or ""))
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
