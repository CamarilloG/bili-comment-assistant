from __future__ import annotations

import os
import sys
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from modules.bot_module import BotModule
from ai_center.event_bus import EventBus
from ai_center.state_machine import TaskStateMachine
from ai_center.model_router import ModelRouter, ModelRouterConfig, ProviderConfig, ModelRoute
from ai_center.planner import Planner
from ai_center.dispatcher import Dispatcher
from ai_center.validator import Validator
from ai_center.executor import Executor
from ai_center.reporter import Reporter

logger = get_logger()

# Shared singletons
registry = ModuleRegistry()
event_bus = EventBus()
browser_pool = BrowserPool()
model_router = ModelRouter()

planner: Planner | None = None
dispatcher: Dispatcher | None = None
validator: Validator | None = None
executor: Executor | None = None
reporter = Reporter()

# Active sessions
sessions: Dict[str, Any] = {}


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
    registry.register("bot", BotModule())
    registry.register("browser_pool", BrowserPoolModule(browser_pool))


def _init_ai_center(config: Dict[str, Any] | None = None) -> None:
    global planner, dispatcher, validator, executor

    from core.models_registry import get_model_by_id

    model_id = (config or {}).get("ai", {}).get("model_id") or ""
    model_cfg = get_model_by_id(model_id) if model_id else None
    has_valid_key = bool(model_cfg and (model_cfg.get("api_key") or "").strip())
    if not has_valid_key:
        logger.warning("AI ????????? API Key??? config ? models_config ???")
    if has_valid_key and model_cfg:
        ai_cfg = config["ai"]
        timeout = max(5, int(ai_cfg.get("timeout", 30)))
        max_retries = max(0, int(ai_cfg.get("max_retries", 2)))
        router_cfg = ModelRouterConfig(
            providers={
                model_id: ProviderConfig(
                    base_url=model_cfg.get("base_url", ""),
                    api_key=model_cfg.get("api_key", ""),
                    model=model_cfg.get("model", ""),
                    timeout=timeout,
                    max_retries=max_retries,
                ),
            },
            routes={
                "planning": ModelRoute(primary_model=model_id),
                "comment_gen": ModelRoute(primary_model=model_id),
                "video_filter": ModelRoute(primary_model=model_id),
                "validation": ModelRoute(primary_model=model_id),
                "summarize": ModelRoute(primary_model=model_id),
            },
        )
        model_router.update_config(router_cfg)

    fsm = TaskStateMachine(event_bus)
    planner = Planner(registry, model_router)
    dispatcher = Dispatcher(registry, browser_pool, event_bus)
    validator = Validator(model_router)
    executor = Executor(planner, dispatcher, validator, event_bus, fsm)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Control Center...")
    try:
        from core.config import ConfigValidator
        config = ConfigValidator.load_config()
    except Exception:
        config = {}

    _register_modules(config)
    _init_ai_center(config)

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

    # 控制台提示信息
    print("Bili Comment Assistant Web panel is running.", flush=True)
    print("Please open http://localhost:9527/panel/ in your browser.", flush=True)
    print("Version: 3.6.0  Developer: CamarilloG  Repo: https://github.com/CamarilloG/bili-comment-assistant", flush=True)

    # 注意：不再自动打开浏览器，避免与 GUI 启动器冲突
    # 如果需要自动打开，请在启动器中控制

    yield

    logger.info("Shutting down AI Control Center...")
    await browser_pool.shutdown()


app = FastAPI(
    title="Bilibili Comment Assistant ??AI Control Center",
    version="3.6.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
from web.routers.session_router import router as session_router
from web.routers.module_router import router as module_router
from web.routers.model_router_api import router as model_api_router
from web.routers.browser_router import router as browser_api_router
from web.routers.config_api import router as config_api_router
from web.routers.task_api import router as task_api_router
from web.routers.auth_api import router as auth_api_router
from web.routers.log_api import router as log_api_router
from web.routers.file_api import router as file_api_router
from web.routers.instances_api import router as instances_api_router
from web.routers.notification_api import router as notification_api_router
from web.websocket.ws_handler import router as ws_router

app.include_router(session_router, prefix="/api/session", tags=["session"])
app.include_router(instances_api_router, prefix="/api/instances", tags=["instances"])
app.include_router(module_router, prefix="/api/modules", tags=["modules"])
app.include_router(model_api_router, prefix="/api/models", tags=["models"])
app.include_router(browser_api_router, prefix="/api/browsers", tags=["browsers"])
app.include_router(config_api_router, prefix="/api/config", tags=["config"])
app.include_router(task_api_router, prefix="/api/task", tags=["task"])
app.include_router(auth_api_router, prefix="/api/auth", tags=["auth"])
app.include_router(log_api_router)
app.include_router(file_api_router, prefix="/api/file", tags=["file"])
app.include_router(notification_api_router)
app.include_router(ws_router)

# ??????PyInstaller ???? _MEIPASS ???????????????
if getattr(sys, "frozen", False):
    _web_base = os.path.join(sys._MEIPASS, "web")
else:
    _web_base = os.path.dirname(__file__)
panel_dir = os.path.join(_web_base, "frontend-v2", "dist")
panel_assets_dir = os.path.join(panel_dir, "assets")
panel_index_path = os.path.join(panel_dir, "index.html")

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
async def chrome_devtools_well_known() -> Dict[str, Any]:
    """Chrome DevTools ????????????? JSON ?? 404?"""
    return {}

# Panel SPA???? /panel/assets????/panel??panel/xxx ?? index.html?????? /panel/ai ????404??
if os.path.isdir(panel_dir):
    if os.path.isdir(panel_assets_dir):
        app.mount("/panel/assets", StaticFiles(directory=panel_assets_dir), name="panel_assets")

    from fastapi.responses import FileResponse

    @app.get("/panel")
    async def panel_index():
        if os.path.exists(panel_index_path):
            return FileResponse(panel_index_path, media_type="text/html")
        return {"error": "Panel not built"}

    @app.get("/panel/{full_path:path}")
    async def panel_spa_fallback(full_path: str):
        # /panel/assets/* ???? mount ????????
        if os.path.exists(panel_index_path):
            return FileResponse(panel_index_path, media_type="text/html")
        return {"error": "Panel not built"}

# ?? frontend ?? /app????mount("/") ?? /ws??api????????WebSocket ????
frontend_dir = os.path.join(_web_base, "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


def start_web_server(host: str = "0.0.0.0", port: int = 9527) -> None:
    import uvicorn
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "loggers": {
            "uvicorn": {"level": "CRITICAL"},
            "uvicorn.access": {"level": "CRITICAL"},
        },
    }
    uvicorn.run(app, host=host, port=port, access_log=False, log_config=log_config)
