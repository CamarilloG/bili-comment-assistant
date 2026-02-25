from __future__ import annotations

import base64

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

router = APIRouter()


@router.get("/status")
async def pool_status():
    from web.app import browser_pool
    return browser_pool.get_pool_status()


@router.get("/{browser_id}/screenshot")
async def browser_screenshot(browser_id: str):
    from web.app import browser_pool

    ctx = browser_pool.get_context(browser_id)
    if ctx is None:
        raise HTTPException(404, f"Browser '{browser_id}' not found")

    pages = ctx.pages
    if not pages:
        raise HTTPException(404, "No open pages in this browser")

    try:
        screenshot_bytes = await pages[0].screenshot(type="png")
        return Response(content=screenshot_bytes, media_type="image/png")
    except Exception as e:
        raise HTTPException(500, f"Screenshot failed: {e}")
