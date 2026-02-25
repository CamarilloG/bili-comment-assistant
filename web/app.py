from __future__ import annotations

import os
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
    registry.register("browser_pool", BrowserPoolModule(browser_pool))


def _init_ai_center(config: Dict[str, Any] | None = None) -> None:
    global planner, dispatcher, validator, executor

    raw_key = config.get("ai", {}).get("api_key", "") if config else ""
    has_valid_key = bool(raw_key) and raw_key not in ("YOUR_API_KEY_HERE", "")
    if not has_valid_key:
        logger.warning("AI api_key not configured — edit config.yaml to enable AI planning")
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
                "planning": ModelRoute(primary_model="default"),
                "comment_gen": ModelRoute(primary_model="default"),
                "video_filter": ModelRoute(primary_model="default"),
                "validation": ModelRoute(primary_model="default"),
                "summarize": ModelRoute(primary_model="default"),
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
    yield

    logger.info("Shutting down AI Control Center...")
    await browser_pool.shutdown()


app = FastAPI(
    title="Bilibili Comment Assistant — AI Control Center",
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

# Mount routers
from web.routers.session_router import router as session_router
from web.routers.module_router import router as module_router
from web.routers.model_router_api import router as model_api_router
from web.routers.browser_router import router as browser_api_router
from web.websocket.ws_handler import router as ws_router

app.include_router(session_router, prefix="/api/session", tags=["session"])
app.include_router(module_router, prefix="/api/modules", tags=["modules"])
app.include_router(model_api_router, prefix="/api/models", tags=["models"])
app.include_router(browser_api_router, prefix="/api/browsers", tags=["browsers"])
app.include_router(ws_router)

# Redirect /panel and /panel/ to frontend root (for portable menu URL)
@app.get("/panel")
@app.get("/panel/")
def _redirect_panel():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=302)


# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


def start_web_server(host: str = "0.0.0.0", port: int = 8080) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)
