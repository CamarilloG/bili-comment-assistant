# 多槽位多开：槽位工作目录与路径
from __future__ import annotations

import json
import os
import threading
from typing import List

# 全局锁，保护 add_slot 和 delete_slot 的并发操作
_slot_operation_lock = threading.Lock()

# 获取软件根目录（exe 所在目录或开发环境的项目根目录）
def _get_software_root() -> str:
    """获取软件根目录"""
    import sys
    if getattr(sys, "frozen", False):
        # 打包后：exe 所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境：项目根目录（bili-bot/）
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# 用户数据目录：软件根目录下的"用户数据"文件夹
_USER_DATA_DIR = os.path.join(_get_software_root(), "用户数据")

# app 根目录（仅用于兼容旧代码）
_APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# 默认槽位数量（0, 1, 2）——仅用于兼容旧逻辑，实际槽位列表由磁盘扫描决定
DEFAULT_SLOT_COUNT = 3


def get_app_root() -> str:
    """返回 app 根目录（与 core/config 的 _CONFIG_DIR 一致）。"""
    return _APP_ROOT


def get_user_data_dir() -> str:
    """返回用户数据目录"""
    os.makedirs(_USER_DATA_DIR, exist_ok=True)
    return _USER_DATA_DIR


def get_workdir(slot_id: str) -> str:
    """槽位 0 用用户数据根目录，其余用用户数据/instances/<slot_id>/。"""
    # 验证 slot_id 只包含数字，防止路径遍历攻击
    if not slot_id.isdigit():
        raise ValueError(f"Invalid slot ID: {slot_id}. Slot ID must be numeric.")
    if slot_id == "0":
        return get_user_data_dir()
    return os.path.join(get_user_data_dir(), "instances", slot_id)


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
        import copy
        from core.config import ConfigValidator
        default = copy.deepcopy(ConfigValidator.DEFAULT_CONFIG)
        default.setdefault("search", {})["keywords"] = ["示例关键词"]
        default.setdefault("comment", {})["texts"] = ["默认评论"]
        ConfigValidator.save_config(default, config_path)
    cookie_path = get_cookie_path(slot_id)
    if not os.path.exists(cookie_path):
        with open(cookie_path, "w", encoding="utf-8") as f:
            json.dump([], f)
    return workdir


def list_slot_ids(max_slots: int | None = None) -> List[str]:
    """返回槽位 ID 列表：始终包含 '0'，其余来自用户数据/instances 目录的数字子目录。"""
    ids = {"0"}
    instances_root = os.path.join(get_user_data_dir(), "instances")
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
    使用线程锁防止并发创建相同 ID 的槽位。
    """
    with _slot_operation_lock:
        ids = list_slot_ids()
        existing_nums = [int(s) for s in ids if s.isdigit() and s != "0"]
        if max_slots is not None and len(existing_nums) >= max_slots:
            raise ValueError(f"已达到最大实例数上限: {max_slots}")

        next_id = 1 if not existing_nums else max(existing_nums) + 1
        ensure_slot_dir(str(next_id))
        return str(next_id)


def delete_slot(slot_id: str) -> bool:
    """
    删除指定槽位目录及其所有文件。
    不允许删除槽位 0。
    返回是否成功删除。
    使用线程锁防止并发删除冲突。
    """
    if slot_id == "0":
        raise ValueError("不能删除槽位 0")

    if not slot_id.isdigit():
        raise ValueError(f"无效的槽位 ID: {slot_id}")

    with _slot_operation_lock:
        workdir = get_workdir(slot_id)
        if not os.path.exists(workdir):
            return False

        import shutil
        try:
            shutil.rmtree(workdir)
            return True
        except Exception as e:
            raise RuntimeError(f"删除槽位失败: {e}")

