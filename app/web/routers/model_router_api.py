from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RoutesUpdateBody(BaseModel):
    routes: Dict[str, Any]


class TestModelBody(BaseModel):
    model_id: str


@router.get("")
async def list_models():
    from web.app import model_router
    from core.models_registry import list_models as registry_list
    models = registry_list(include_secrets=False)
    return {
        "models": [{"id": m["id"], "model_name": m["model_name"], "price": m.get("price", "")} for m in models],
        "available_models": model_router.get_available_models(),
        "routes": {
            k: v.model_dump() for k, v in model_router.get_routes().items()
        },
    }


@router.post("/test")
async def test_model_connection(body: TestModelBody):
    """用当前选中的 model_id 测一次调用。"""
    from core.models_registry import get_model_by_id
    from core.ai_provider import AIProvider
    model_cfg = get_model_by_id(body.model_id)
    if not model_cfg:
        return {"ok": False, "message": "模型不存在"}
    if not (model_cfg.get("api_key") or "").strip():
        return {"ok": False, "message": "该模型未配置 API Key"}
    try:
        provider = AIProvider(model_cfg, timeout=15, max_retries=1)
        out = provider.chat("You are a helper.", "hi", max_tokens=32)
        return {"ok": bool(out), "message": "OK" if out else "无响应"}
    except Exception as e:
        return {"ok": False, "message": str(e)}


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
