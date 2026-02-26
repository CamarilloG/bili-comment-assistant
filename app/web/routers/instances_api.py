from __future__ import annotations

from fastapi import APIRouter

from core.slot import list_slot_ids

router = APIRouter()


@router.get("")
async def get_instances():
    """返回槽位列表，供前端实例切换器使用。"""
    ids = list_slot_ids()
    return {"slots": [{"id": sid, "label": f"实例 {sid}"} for sid in ids]}
