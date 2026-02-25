from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RoutesUpdateBody(BaseModel):
    routes: Dict[str, Any]


@router.get("")
async def list_models():
    from web.app import model_router
    return {
        "available_models": model_router.get_available_models(),
        "routes": {
            k: v.model_dump() for k, v in model_router.get_routes().items()
        },
    }


@router.put("/routes")
async def update_routes(body: RoutesUpdateBody):
    from web.app import model_router
    from ai_center.model_router import ModelRoute

    new_routes = {}
    for task_type, route_data in body.routes.items():
        if isinstance(route_data, dict):
            new_routes[task_type] = ModelRoute(**route_data)
        else:
            new_routes[task_type] = route_data
    model_router._config.routes = new_routes
    return {"status": "updated", "routes": body.routes}
