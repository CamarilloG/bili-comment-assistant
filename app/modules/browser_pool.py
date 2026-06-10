from __future__ import annotations

import asyncio
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from modules.base import (
    ActionResult,
    ActionSpec,
    ExecutionContext,
    IModule,
    ModuleCapability,
    ParamSpec,
)
from utils.logger import get_logger

logger = get_logger()


class BrowserInstance(BaseModel):
    """Metadata for a single managed browser."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:8])
    status: str = "idle"  # idle, active, closed
    page_ids: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class BrowserPoolConfig(BaseModel):
    max_browsers: int = 3
    initial_browsers: int = 1
    headless: bool = False
    executable_path: str = ""
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1280
    viewport_height: int = 720
    extra_args: List[str] = Field(default_factory=lambda: [
        "--disable-infobars",
        "--disable-blink-features=AutomationControlled",
        "--mute-audio",
        "--disable-gpu",
        "--disable-dev-shm-usage",
    ])


class BrowserPool:
    """Manages multiple async Playwright browser instances."""

    def __init__(self, config: BrowserPoolConfig | None = None) -> None:
        self.config = config or BrowserPoolConfig()
        self._playwright: Any = None
        self._browsers: Dict[str, Any] = {}       # id -> browser
        self._contexts: Dict[str, Any] = {}        # id -> context
        self._pages: Dict[str, Any] = {}           # page_id -> page
        self._meta: Dict[str, BrowserInstance] = {}
        self._available: asyncio.Queue[str] = asyncio.Queue()
        self._initialized = False

    async def initialize(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        for _ in range(self.config.initial_browsers):
            await self._create_browser()
        self._initialized = True
        logger.info(f"BrowserPool initialized with {len(self._meta)} browser(s)")

    async def _create_browser(self, status: str = "idle") -> BrowserInstance:
        launch_args: Dict[str, Any] = {
            "headless": self.config.headless,
            "args": list(self.config.extra_args) + [
                f"--window-size={self.config.viewport_width},{self.config.viewport_height}",
            ],
        }
        exe = self.config.executable_path
        if exe and os.path.exists(exe):
            launch_args["executable_path"] = os.path.normpath(exe)
            launch_args["ignore_default_args"] = ["--no-sandbox"]

        browser = await self._playwright.chromium.launch(**launch_args)
        try:
            ctx = await browser.new_context(
                user_agent=self.config.user_agent,
                viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            )
            await ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            meta = BrowserInstance(status=status)
            self._browsers[meta.id] = browser
            self._contexts[meta.id] = ctx
            self._meta[meta.id] = meta
            if status == "idle":
                await self._available.put(meta.id)
            return meta
        except Exception:
            # 如果 context 创建失败，关闭 browser 避免泄漏
            try:
                await browser.close()
            except Exception:
                pass
            raise

    async def acquire(self, timeout: float = 30) -> BrowserInstance:
        try:
            bid = await asyncio.wait_for(self._available.get(), timeout=timeout)
            meta = self._meta[bid]
            meta.status = "active"
            return meta
        except asyncio.TimeoutError:
            if len(self._meta) < self.config.max_browsers:
                return await self._create_browser(status="active")
            raise RuntimeError("No browser available and pool is at capacity")

    async def release(self, browser_id: str) -> None:
        meta = self._meta.get(browser_id)
        if meta is None:
            return
        ctx = self._contexts.get(browser_id)
        if ctx:
            for page in ctx.pages:
                try:
                    await page.close()
                except Exception:
                    pass
        meta.page_ids.clear()
        meta.status = "idle"
        await self._available.put(browser_id)

    async def create_page(self, browser_id: str) -> str:
        ctx = self._contexts.get(browser_id)
        if ctx is None:
            raise KeyError(f"Browser {browser_id} not found")
        page = await ctx.new_page()
        page_id = uuid.uuid4().hex[:8]
        self._pages[page_id] = page
        self._meta[browser_id].page_ids.append(page_id)
        return page_id

    def get_page(self, page_id: str) -> Any:
        return self._pages.get(page_id)

    def get_context(self, browser_id: str) -> Any:
        return self._contexts.get(browser_id)

    async def close_page(self, page_id: str) -> None:
        page = self._pages.pop(page_id, None)
        if page:
            await page.close()
        for meta in self._meta.values():
            if page_id in meta.page_ids:
                meta.page_ids.remove(page_id)

    def get_pool_status(self) -> Dict[str, Any]:
        statuses = [m.status for m in self._meta.values()]
        return {
            "total": len(self._meta),
            "active": statuses.count("active"),
            "idle": statuses.count("idle"),
            "browsers": [
                {"id": m.id, "status": m.status, "pages": len(m.page_ids)}
                for m in self._meta.values()
            ],
        }

    async def shutdown(self) -> None:
        for page in list(self._pages.values()):
            try:
                await page.close()
            except Exception:
                pass
        self._pages.clear()

        for bid, browser in list(self._browsers.items()):
            try:
                await browser.close()
            except Exception:
                pass
        self._browsers.clear()
        self._contexts.clear()
        self._meta.clear()

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._initialized = False
        logger.info("BrowserPool shut down")


class BrowserPoolModule(IModule):
    """Exposes BrowserPool operations through the standard module interface."""

    def __init__(self, pool: BrowserPool | None = None) -> None:
        self.pool = pool or BrowserPool()

    def get_capability(self) -> ModuleCapability:
        return ModuleCapability(
            name="browser_pool",
            description="浏览器池管理模块，管理多个Playwright浏览器实例的创建/分配/回收",
            actions=[
                ActionSpec(
                    name="acquire_browser",
                    description="获取一个可用浏览器实例",
                    returns={"browser_id": "str"},
                    estimated_duration="medium",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="release_browser",
                    description="归还浏览器实例",
                    parameters={
                        "browser_id": ParamSpec(type="string", description="浏览器实例ID"),
                    },
                    returns={"released": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="create_page",
                    description="在指定浏览器中创建新页面",
                    parameters={
                        "browser_id": ParamSpec(type="string", description="浏览器实例ID"),
                    },
                    returns={"page_id": "str"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="close_page",
                    description="关闭指定页面",
                    parameters={
                        "page_id": ParamSpec(type="string", description="页面ID"),
                    },
                    returns={"closed": "bool"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
                ActionSpec(
                    name="get_pool_status",
                    description="获取浏览器池状态",
                    returns={"total": "int", "active": "int", "idle": "int", "browsers": "list"},
                    estimated_duration="fast",
                    risk_level="safe",
                ),
            ],
            requires_browser=False,
            requires_auth=False,
            category="system",
        )

    async def execute(
        self, action: str, params: Dict[str, Any], context: ExecutionContext
    ) -> ActionResult:
        self._require_action(action)

        try:
            if action == "acquire_browser":
                instance = await self.pool.acquire()
                return ActionResult(success=True, data={"browser_id": instance.id})

            if action == "release_browser":
                await self.pool.release(params["browser_id"])
                return ActionResult(success=True, data={"released": True})

            if action == "create_page":
                page_id = await self.pool.create_page(params["browser_id"])
                return ActionResult(success=True, data={"page_id": page_id})

            if action == "close_page":
                await self.pool.close_page(params["page_id"])
                return ActionResult(success=True, data={"closed": True})

            if action == "get_pool_status":
                status = self.pool.get_pool_status()
                return ActionResult(success=True, data=status)

        except Exception as exc:
            return ActionResult(success=False, error=str(exc))

        return ActionResult(success=False, error="Unreachable")

    async def validate_params(self, action: str, params: Dict[str, Any]) -> tuple[bool, str]:
        self._require_action(action)
        if action == "release_browser" and not params.get("browser_id"):
            return False, "browser_id is required"
        if action == "create_page" and not params.get("browser_id"):
            return False, "browser_id is required"
        if action == "close_page" and not params.get("page_id"):
            return False, "page_id is required"
        return True, ""

    async def health_check(self) -> bool:
        return self.pool._initialized
