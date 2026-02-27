# 多槽位多开：槽位工作目录与路径
from __future__ import annotations

import json
import os
from typing import List

# 与 config 一致：app 根目录
_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 默认槽位数量（0, 1, 2）——仅用于兼容旧逻辑，实际槽位列表由磁盘扫描决定
DEFAULT_SLOT_COUNT = 3


def get_app_root() -> str:
    """返回 app 根目录（与 core/config 的 _CONFIG_DIR 一致）。"""
    return _APP_ROOT


def get_workdir(slot_id: str) -> str:
    """槽位 0 用 app 根目录，其余用 instances/<slot_id>/。"""
    if slot_id == "0":
        return _APP_ROOT
    return os.path.join(_APP_ROOT, "instances", slot_id)


def get_config_path(slot_id: str) -> str:
    return os.path.join(get_workdir(slot_id), "config.yaml")


def get_cookie_path(slot_id: str) -> str:
    return os.path.join(get_workdir(slot_id), "cookies.json")


def get_history_path(slot_id: str) -> str:
    return os.path.join(get_workdir(slot_id), "history.json")


def get_comment_log_path(slot_id: str) -> str:
    return os.path.join(get_workdir(slot_id), "comment_log.csv")


def get_qrcode_path(slot_id: str) -> str:
    return os.path.join(get_workdir(slot_id), "login_qrcode.png")


def ensure_slot_dir(slot_id: str) -> str:
    """确保槽位目录存在；非 0 且目录为空时写入默认 config 与空 cookies。返回 workdir。"""
    workdir = get_workdir(slot_id)
    if slot_id == "0":
        return workdir
    os.makedirs(workdir, exist_ok=True)
    config_path = get_config_path(slot_id)
    if not os.path.exists(config_path):
        from core.config import ConfigValidator
        default = dict(ConfigValidator.DEFAULT_CONFIG)
        default.setdefault("search", {})["keywords"] = ["示例关键词"]
        default.setdefault("comment", {})["texts"] = ["默认评论"]
        ConfigValidator.save_config(default, config_path)
    cookie_path = get_cookie_path(slot_id)
    if not os.path.exists(cookie_path):
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump([], f)
    return workdir


def list_slot_ids(max_slots: int | None = None) -> List[str]:
    """返回槽位 ID 列表：始终包含 '0'，其余来自 instances 目录的数字子目录。"""
    ids = {"0"}
    instances_root = os.path.join(_APP_ROOT, "instances")
    if os.path.isdir(instances_root):
        for name in os.listdir(instances_root):
            # 仅接受纯数字目录名作为实例 ID
            if name.isdigit():
                ids.add(name)
    result = sorted(ids, key=lambda x: int(x))
    if max_slots is not None:
        return result[:max_slots]
    return result


def add_slot(max_slots: int | None = None) -> str:
    """
    创建一个新的非 0 槽位目录并返回其 ID。
    max_slots 为可选上限（不含槽位 0）。
    """
    ids = list_slot_ids()
    existing_nums = [int(s) for s in ids if s.isdigit() and s != "0"]
    if max_slots is not None and len(existing_nums) >= max_slots:
        raise ValueError(f"已达到最大实例数上限: {max_slots}")

    next_id = 1 if not existing_nums else max(existing_nums) + 1
    ensure_slot_dir(str(next_id))
    return str(next_id)

