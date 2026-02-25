from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from utils.logger import get_logger
from modules.registry import ModuleRegistry
from modules.browser_pool import BrowserPool, BrowserPoolConfig, BrowserPoolModule
from modules.auth_module import AuthModule
from modules.search_module import SearchModule
from modules.comment_module import CommentModule
from modules.warmup_module import WarmupModule
from modules.ai_gen_module import AIGenModule
from modules.ai_filter_module import AIFilterModule
from modules.history_module import HistoryModule
from modules.captcha_module import CaptchaModule
from modules.config_module import ConfigModule
from modules.notify_module import NotifyModule
from modules.report_module import ReportModule
from ai_center.model_router import ModelRouter, ModelRouterConfig, ProviderConfig, ModelRoute

logger = get_logger()

# Shared singletons（仅保留 model_router，AI 中控台已废弃）
registry = ModuleRegistry()
browser_pool = BrowserPool()
model_router = ModelRouter()


def _register_modules(config: Dict[str, Any] | None = None) -> None:
    config = config or {}
    registry.register("auth", AuthModule())
    registry.register("search", SearchModule())
    registry.register("comment", CommentModule())
    warmup = WarmupModule()
    warmup.set_config(config)
    registry.register("warmup", warmup)
    registry.register("ai_gen", AIGenModule(config))
    registry.register("ai_filter", AIFilterModule(config))
    registry.register("history", HistoryModule())
    registry.register("captcha", CaptchaModule())
    registry.register("config", ConfigModule())
    registry.register("notify", NotifyModule())
    registry.register("report", ReportModule())
    registry.register("browser_pool", BrowserPoolModule(browser_pool))


def _init_model_router(config: Dict[str, Any] | None = None) -> None:
    """配置 AI 模型路由（供评论生成等使用）。"""
    raw_key = config.get("ai", {}).get("api_key", "") if config else ""
    has_valid_key = bool(raw_key) and raw_key not in ("YOUR_API_KEY_HERE", "")
    if not has_valid_key:
        logger.warning("AI api_key not configured — edit config.yaml to enable AI features")
    if has_valid_key:
        ai_cfg = config["ai"]
        router_cfg = ModelRouterConfig(
            providers={
                "default": ProviderConfig(
                    base_url=ai_cfg.get("base_url", "https://api.deepseek.com/v1"),
                    api_key=ai_cfg["api_key"],
                    model=ai_cfg.get("model", "deepseek-chat"),
                    timeout=ai_cfg.get("timeout", 30),
                    max_retries=ai_cfg.get("max_retries", 2),
                ),
            },
            routes={
                "comment_gen": ModelRoute(primary_model="default"),
                "video_filter": ModelRoute(primary_model="default"),
                "summarize": ModelRoute(primary_model="default"),
            },
        )
        model_router.update_config(router_cfg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Control Center...")
    try:
        from core.config import ConfigValidator
        config = ConfigValidator.load_config()
    except Exception:
        config = {}

    _register_modules(config)
    _init_model_router(config)

    pool_cfg = BrowserPoolConfig(
        headless=config.get("behavior", {}).get("headless", False),
        executable_path=config.get("browser", {}).get("path", ""),
    )
    browser_pool.config = pool_cfg
    try:
        await browser_pool.initialize()
    except Exception as e:
        logger.warning(f"BrowserPool init skipped: {e}")

    logger.info(f"Registered modules: {registry.list_ids()}")
    yield

    logger.info("Shutting down Control Center...")
    await browser_pool.shutdown()


app = FastAPI(
    title="Bilibili Comment Assistant — Control Panel",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers（已移除 AI 中控台 session API）
from web.routers.module_router import router as module_router
from web.routers.model_router_api import router as model_api_router
from web.routers.browser_router import router as browser_api_router
from web.routers.log_api import router as log_api_router
from web.routers.config_api import router as config_api_router
from web.routers.task_api import router as task_api_router
from web.routers.auth_api import router as auth_api_router
from web.routers.file_api import router as file_api_router
from web.websocket.ws_handler import router as ws_router

app.include_router(module_router, prefix="/api/modules", tags=["modules"])
app.include_router(model_api_router, prefix="/api/models", tags=["models"])
app.include_router(browser_api_router, prefix="/api/browsers", tags=["browsers"])
app.include_router(config_api_router, prefix="/api/config", tags=["config"])
app.include_router(task_api_router, prefix="/api/task", tags=["task"])
app.include_router(auth_api_router, prefix="/api/auth", tags=["auth"])
app.include_router(file_api_router, prefix="/api/file", tags=["file"])
app.include_router(log_api_router)
app.include_router(ws_router)

# 仅挂载 Vue 控制面板（已废弃 AI 中控台，不再挂载 web/frontend）
@app.get("/", include_in_schema=False)
def _redirect_root():
    return RedirectResponse(url="/panel/", status_code=302)

panel_dir = os.path.join(os.path.dirname(__file__), "frontend-v2", "dist")
if os.path.isdir(panel_dir):
    app.mount("/panel", StaticFiles(directory=panel_dir, html=True), name="panel")
else:
    logger.warning("frontend-v2/dist not found — run npm run build in web/frontend-v2")


def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)
