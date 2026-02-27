from __future__ import annotations

from fastapi import APIRouter

from core.slot import add_slot, list_slot_ids

router = APIRouter()


@router.get("")
async def get_instances():
    """返回槽位列表，供前端实例切换器使用。"""
    ids = list_slot_ids()
    return {"slots": [{"id": sid, "label": f"实例 {sid}"} for sid in ids]}


@router.post("")
async def add_instance():
    """创建一个新的实例槽位并返回最新列表。"""
    new_id = add_slot()
    ids = list_slot_ids()
    return {
        "id": new_id,
        "slots": [{"id": sid, "label": f"实例 {sid}"} for sid in ids],
    }

