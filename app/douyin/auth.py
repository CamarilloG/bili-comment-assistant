# 抖音登录态：本地保存/加载 Cookie，后续请求默认携带。
# 与 B 站 core/auth 无耦合；仅用于 douyin 模块。

from __future__ import annotations

import json
import os
from typing import Any, List

from playwright.sync_api import BrowserContext, Page
from utils.logger import get_logger

logger = get_logger()

# 存放路径：用户数据/douyin_cookies.json
def _get_douyin_cookie_path() -> str:
    from core.slot import get_user_data_dir
    return os.path.join(get_user_data_dir(), "douyin_cookies.json")


# Playwright 可用的 cookie 需含 name, value, domain, path；domain 建议 .douyin.com 或 https://www.douyin.com
DOUYIN_DOMAINS = ("douyin.com", ".douyin.com", "www.douyin.com", "login.douyin.com")


def _normalize_cookie_for_playwright(c: dict) -> dict:
    """确保包含 domain/path，便于 add_cookies。"""
    out = {"name": c["name"], "value": c.get("value", "")}
    domain = c.get("domain", "").strip()
    if not domain or not any(d in domain for d in ("douyin", ".douyin")):
        out["domain"] = ".douyin.com"
    else:
        out["domain"] = domain if domain.startswith(".") else "." + domain.lstrip(".")
    out["path"] = c.get("path", "/")
    if "expires" in c:
        out["expires"] = c["expires"]
    if c.get("httpOnly") is not None:
        out["httpOnly"] = c["httpOnly"]
    if c.get("secure") is not None:
        out["secure"] = c["secure"]
    if c.get("sameSite") is not None:
        out["sameSite"] = c["sameSite"]
    return out


def load_douyin_cookies() -> List[dict]:
    """从本地文件加载抖音 Cookie 列表（Playwright 格式）。"""
    path = _get_douyin_cookie_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"[抖音] 读取 Cookie 文件失败: {e}")
        return []
    cookies = data.get("cookies") if isinstance(data, dict) else data
    if not isinstance(cookies, list):
        return []
    return [_normalize_cookie_for_playwright(c) for c in cookies if c.get("name")]


def save_douyin_cookies(cookies: List[dict], meta: dict | None = None) -> bool:
    """将抖音 Cookie 保存到本地；meta 可含 updated_at、capture_method_ref 等。"""
    path = _get_douyin_cookie_path()
    try:
        data = {
            "cookies": cookies,
            "updated_at": meta.get("updated_at") if meta else None,
            "capture_method_ref": "docs/douyin_capture_method.md",
        }
        if meta:
            for k, v in meta.items():
                if k not in data and v is not None:
                    data[k] = v
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"[抖音] Cookie 已保存至 {path}")
        return True
    except Exception as e:
        logger.error(f"[抖音] 保存 Cookie 失败: {e}")
        return False


def inject_douyin_cookies(context: BrowserContext) -> bool:
    """向 BrowserContext 注入本地抖音 Cookie，后续访问 douyin 会默认携带。"""
    cookies = load_douyin_cookies()
    if not cookies:
        return False
    try:
        context.add_cookies(cookies)
        logger.debug(f"[抖音] 已注入 {len(cookies)} 个 Cookie")
        return True
    except Exception as e:
        logger.warning(f"[抖音] 注入 Cookie 失败: {e}")
        return False


def inject_douyin_cookies_to_page(page: Page) -> bool:
    """通过 page 的 context 注入本地抖音 Cookie。"""
    return inject_douyin_cookies(page.context)


def get_douyin_cookie_path() -> str:
    """供外部或文档使用：返回当前使用的 Cookie 文件路径。"""
    return _get_douyin_cookie_path()


def save_douyin_cookies_from_header(cookie_header: str) -> bool:
    """从请求头 Cookie 字符串（name=value; name2=value2）解析并保存，domain 设为 .douyin.com。"""
    if not cookie_header or not cookie_header.strip():
        return False
    cookies = []
    for part in cookie_header.strip().split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        name, value = name.strip(), value.strip()
        if name:
            cookies.append({
                "name": name,
                "value": value,
                "domain": ".douyin.com",
                "path": "/",
            })
    return save_douyin_cookies(cookies, meta={"updated_at": "from_header"})
