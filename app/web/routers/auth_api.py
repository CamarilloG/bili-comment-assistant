from __future__ import annotations

import base64
import json
import os
import threading

from fastapi import APIRouter, HTTPException

from core.config import ConfigValidator
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

_auth_state = {
    "checking": False,
    "logged_in": None,
    "qr_login_running": False,
}


@router.get("/status")
async def auth_status():
    cookie_file = "cookies.json"
    has_cookies = os.path.exists(cookie_file)
    return {
        "has_cookies": has_cookies,
        "logged_in": _auth_state["logged_in"],
        "checking": _auth_state["checking"],
    }


@router.post("/check")
async def check_login():
    if _auth_state["checking"]:
        return {"status": "already_checking"}

    _auth_state["checking"] = True

    def _check():
        try:
            from playwright.sync_api import sync_playwright
            import main as backend_main

            config = ConfigValidator.load_config()
            launch_args = backend_main.get_browser_launch_args(config)
            if not launch_args:
                _auth_state["logged_in"] = False
                return

            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                from core.auth import AuthManager

                auth = AuthManager(context, "cookies.json")
                if os.path.exists("cookies.json"):
                    with open("cookies.json", "r", encoding="utf-8") as f:
                        context.add_cookies(json.load(f))
                _auth_state["logged_in"] = auth._check_login_status()
                browser.close()
        except Exception as e:
            logger.error(f"Login check failed: {e}")
            _auth_state["logged_in"] = False
        finally:
            _auth_state["checking"] = False

    threading.Thread(target=_check, daemon=True).start()
    return {"status": "checking"}


@router.post("/qrcode")
async def qr_login():
    if _auth_state["qr_login_running"]:
        return {"status": "already_running"}

    _auth_state["qr_login_running"] = True

    def _login():
        try:
            from playwright.sync_api import sync_playwright
            import main as backend_main

            config = ConfigValidator.load_config()
            launch_args = backend_main.get_browser_launch_args(config, force_headed=True)
            if not launch_args:
                return

            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                from core.auth import AuthManager

                auth = AuthManager(context, "cookies.json")
                result = auth._qr_login()
                _auth_state["logged_in"] = result
                browser.close()
        except Exception as e:
            logger.error(f"QR login failed: {e}")
        finally:
            _auth_state["qr_login_running"] = False

    threading.Thread(target=_login, daemon=True).start()
    return {"status": "started"}


@router.get("/qrcode/image")
async def get_qrcode_image():
    path = "login_qrcode.png"
    if not os.path.exists(path):
        raise HTTPException(404, "QR code image not available")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"image": f"data:image/png;base64,{data}"}
