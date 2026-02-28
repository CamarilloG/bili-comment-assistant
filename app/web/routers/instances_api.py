from __future__ import annotations

from fastapi import APIRouter, HTTPException

from core.slot import add_slot, delete_slot, list_slot_ids

router = APIRouter()

# 最大实例数（不含槽位 0）
MAX_INSTANCES = 10


def _get_slot_running_status(slot_id: str) -> bool:
    """检查指定槽位是否有任务正在运行。"""
    from web.routers.task_api import _task_state, _state_lock

    with _state_lock:
        if slot_id not in _task_state:
            return False
        state = _task_state[slot_id]
        return state["comment"]["running"] or state["warmup"]["running"]


@router.get("")
async def get_instances():
    """返回槽位列表，供前端实例切换器使用。"""
    ids = list_slot_ids()
    slots = []
    for sid in ids:
        is_running = _get_slot_running_status(sid)
        slots.append({
            "id": sid,
            "label": f"实例 {sid}",
            "isRunning": is_running,
            "status": "running" if is_running else "idle",
            "statusLabel": "运行中" if is_running else "空闲"
        })
    return {"slots": slots}


@router.post("")
async def add_instance():
    """创建一个新的实例槽位并返回最新列表。"""
    try:
        new_id = add_slot(max_slots=MAX_INSTANCES)
        ids = list_slot_ids()
        slots = []
        for sid in ids:
            is_running = _get_slot_running_status(sid)
            slots.append({
                "id": sid,
                "label": f"实例 {sid}",
                "isRunning": is_running,
                "status": "running" if is_running else "idle",
                "statusLabel": "运行中" if is_running else "空闲"
            })
        return {"id": new_id, "slots": slots}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{slot_id}")
async def delete_instance(slot_id: str):
    """删除指定的实例槽位。"""
    try:
        success = delete_slot(slot_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"实例 {slot_id} 不存在")
        ids = list_slot_ids()
        slots = []
        for sid in ids:
            is_running = _get_slot_running_status(sid)
            slots.append({
                "id": sid,
                "label": f"实例 {sid}",
                "isRunning": is_running,
                "status": "running" if is_running else "idle",
                "statusLabel": "运行中" if is_running else "空闲"
            })
        return {"success": True, "slots": slots}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

