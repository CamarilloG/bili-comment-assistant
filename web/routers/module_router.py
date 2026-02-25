from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
async def list_modules():
    from web.app import registry
    caps = registry.get_all_capabilities()
    return [
        {"id": c.name, "description": c.description, "category": c.category}
        for c in caps
    ]


@router.get("/{module_id}/capability")
async def get_capability(module_id: str):
    from web.app import registry
    if module_id not in registry:
        raise HTTPException(404, f"Module '{module_id}' not found")
    return registry.get_capability(module_id).model_dump()
