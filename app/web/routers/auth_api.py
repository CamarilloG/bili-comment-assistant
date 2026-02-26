from __future__ import annotations

import base64
import json
import os
import threading
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from core.config import ConfigValidator
from core.slot import get_config_path, get_cookie_path, get_qrcode_path, ensure_slot_dir
from utils.logger import get_logger

logger = get_logger()
router = APIRouter()

# 按槽位：_auth_state[slot_id] = {"checking", "logged_in", "qr_login_running"}
_auth_state: Dict[str, Dict[str, Any]] = {}
_auth_state_lock = threading.Lock()


def _get_auth_state(slot_id: str) -> Dict[str, Any]:
    with _auth_state_lock:
        if slot_id not in _auth_state:
            _auth_state[slot_id] = {
                "checking": False,
                "logged_in": None,
                "qr_login_running": False,
            }
        return _auth_state[slot_id]


@router.get("/status")
async def auth_status(slot: str = Query("0", alias="slot")):
    ensure_slot_dir(slot)
    cookie_path = get_cookie_path(slot)
    has_cookies = os.path.exists(cookie_path)
    state = _get_auth_state(slot)
    return {
        "has_cookies": has_cookies,
        "logged_in": state["logged_in"],
        "checking": state["checking"],
    }


@router.post("/check")
async def check_login(slot: str = Query("0", alias="slot")):
    state = _get_auth_state(slot)
    if state["checking"]:
        return {"status": "already_checking"}

    state["checking"] = True

    def _check():
        try:
            from playwright.sync_api import sync_playwright
            import main as backend_main

            ensure_slot_dir(slot)
            config_path = get_config_path(slot)
            cookie_path = get_cookie_path(slot)
            config = ConfigValidator.load_config(config_path)
            launch_args = backend_main.get_browser_launch_args(config)
            if not launch_args:
                state["logged_in"] = False
                return

            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                from core.auth import AuthManager

                auth = AuthManager(context, cookie_path)
                if os.path.exists(cookie_path):
                    with open(cookie_path, "r", encoding="utf-8") as f:
                        context.add_cookies(json.load(f))
                state["logged_in"] = auth._check_login_status()
                browser.close()
        except Exception as e:
            logger.error(f"Login check failed: {e}")
            state["logged_in"] = False
        finally:
            state["checking"] = False

    threading.Thread(target=_check, daemon=True).start()
    return {"status": "checking"}


@router.post("/qrcode")
async def qr_login(slot: str = Query("0", alias="slot")):
    state = _get_auth_state(slot)
    if state["qr_login_running"]:
        return {"status": "already_running"}

    state["qr_login_running"] = True

    def _login():
        try:
            from playwright.sync_api import sync_playwright
            import main as backend_main

            ensure_slot_dir(slot)
            config_path = get_config_path(slot)
            cookie_path = get_cookie_path(slot)
            qrcode_path = get_qrcode_path(slot)
            config = ConfigValidator.load_config(config_path)
            launch_args = backend_main.get_browser_launch_args(config, force_headed=True)
            if not launch_args:
                return

            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                from core.auth import AuthManager

                auth = AuthManager(context, cookie_path, qrcode_path=qrcode_path)
                result = auth._qr_login()
                state["logged_in"] = result
                browser.close()
        except Exception as e:
            logger.error(f"QR login failed: {e}")
        finally:
            state["qr_login_running"] = False

    threading.Thread(target=_login, daemon=True).start()
    return {"status": "started"}


@router.get("/qrcode/image")
async def get_qrcode_image(slot: str = Query("0", alias="slot")):
    ensure_slot_dir(slot)
    path = get_qrcode_path(slot)
    if not os.path.exists(path):
        raise HTTPException(404, "QR code image not available")
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return {"image": f"data:image/png;base64,{data}"}
