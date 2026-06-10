"""Send direct messages via Playwright on message.bilibili.com and track history."""

from __future__ import annotations

import json
import os
import random
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger()

DM_URL_TEMPLATE = "https://message.bilibili.com/#/whisper/mid{uid}"


class DmHistory:
    """Persistent record of sent DMs, keyed by receiver UID."""

    def __init__(self, path: str):
        self.path = path
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except Exception as e:
                logger.warning(f"[DmHistory] 加载失败: {e}")
                self._data = {}

    def _save(self):
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except Exception as e:
            logger.error(f"[DmHistory] 保存失败: {e}")

    def is_sent(self, uid: str) -> bool:
        return uid in self._data

    def record(self, uid: str, uname: str, status: str):
        self._data[uid] = {
            "uname": uname,
            "sent_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": status,
        }
        self._save()

    @property
    def total_sent(self) -> int:
        return sum(1 for v in self._data.values() if v.get("status") == "ok")

    @property
    def today_sent(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        return sum(
            1 for v in self._data.values()
            if v.get("status") == "ok" and v.get("sent_at", "").startswith(today)
        )


class DmSender:
    """Operate message.bilibili.com whisper page to send DMs."""

    def __init__(self, page: Page, delay_range: Tuple[float, float] = (8.0, 20.0)):
        self.page = page
        self.delay_min, self.delay_max = delay_range

    def send_dm(
        self,
        uid: str,
        content: str,
        stop_event: Optional[threading.Event] = None,
    ) -> str:
        """Send a DM to a user. Returns status string: 'ok', 'limited', 'failed'.

        Navigates to the whisper page, types message, clicks send.
        """
        if stop_event and stop_event.is_set():
            return "stopped"

        url = DM_URL_TEMPLATE.format(uid=uid)
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=15000)
            self.page.wait_for_timeout(3000)
        except Exception as e:
            logger.error(f"[DmSender] 导航到私信页失败 uid={uid}: {e}")
            return "failed"

        if stop_event and stop_event.is_set():
            return "stopped"

        # 等待 SPA 聊天界面渲染完成
        chat_ready = self._wait_for_chat_ui()
        if not chat_ready:
            logger.error(f"[DmSender] 聊天界面未加载 uid={uid}")
            self._dump_page_inputs()
            return "failed"

        try:
            input_el = self._find_chat_input()
            input_el.click()
            self.page.wait_for_timeout(300)

            tag = input_el.evaluate("el => el.tagName")
            if tag == "TEXTAREA":
                input_el.fill("")
                input_el.type(content, delay=random.randint(30, 80))
            else:
                input_el.evaluate("el => el.textContent = ''")
                input_el.type(content, delay=random.randint(30, 80))
            self.page.wait_for_timeout(500)
        except Exception as e:
            logger.error(f"[DmSender] 输入内容失败 uid={uid}: {e}")
            return "failed"

        if stop_event and stop_event.is_set():
            return "stopped"

        try:
            sent = False
            # 方法 1: 尝试找发送按钮
            btn_selectors = [
                "[class*='SendBtn']",
                "div[class*='SendBtn']",
                "button.send-btn",
                "button:has-text('发送')",
                ".chat-input-actions button.primary",
                ".im-send-btn",
                ".send-msg-btn",
                "button.bl-button--primary",
            ]
            for sel in btn_selectors:
                try:
                    btn = self.page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible(timeout=500):
                        btn.click()
                        self.page.wait_for_timeout(800)
                        if self._input_cleared():
                            sent = True
                            logger.debug(f"[DmSender] 通过按钮发送: {sel}")
                        break
                except Exception:
                    continue

            # 方法 2: 键盘发送 (Enter / Ctrl+Enter)
            # 仅当输入框中仍有未发出的内容时才会走到这里，不存在重复发送
            if not sent:
                try:
                    input_el = self._find_chat_input()
                    input_el.press("Enter")
                    self.page.wait_for_timeout(800)
                    if self._input_cleared():
                        sent = True
                        logger.debug("[DmSender] 通过 Enter 键发送")
                except Exception:
                    pass

            if not sent:
                try:
                    input_el = self._find_chat_input()
                    input_el.press("Control+Enter")
                    self.page.wait_for_timeout(800)
                    if self._input_cleared():
                        sent = True
                        logger.debug("[DmSender] 通过 Ctrl+Enter 发送")
                except Exception:
                    pass

            if not sent:
                # dump 按钮信息辅助调试
                try:
                    btns = self.page.evaluate("""() => {
                        const result = [];
                        document.querySelectorAll('button, [role="button"], .btn, a.send').forEach(el => {
                            if (el.offsetWidth > 0 || el.offsetHeight > 0) {
                                result.push({
                                    tag: el.tagName,
                                    text: (el.textContent || '').trim().substring(0, 40),
                                    cls: (el.className || '').toString().substring(0, 80),
                                });
                            }
                        });
                        return result;
                    }""")
                    logger.info(f"[DmSender] 页面可见按钮: {json.dumps(btns, ensure_ascii=False)}")
                except Exception:
                    pass
                raise Exception("所有发送方式均失败（输入框内容未被清空，消息未发出）")

            self.page.wait_for_timeout(1500)
        except Exception as e:
            logger.error(f"[DmSender] 点击发送失败 uid={uid}: {e}")
            return "failed"

        if self._check_send_limit():
            logger.warning(f"[DmSender] 检测到发送限制 uid={uid}")
            return "limited"

        logger.info(f"[DmSender] 私信发送成功 uid={uid}")
        return "ok"

    def _wait_for_chat_ui(self) -> bool:
        """等待私信页面 SPA 的聊天界面完成渲染。"""
        chat_container_selectors = [
            ".im-chat",
            ".chat-container",
            ".im-list",
            ".msg-container",
            "#app .container",
        ]
        for attempt in range(6):
            for sel in chat_container_selectors:
                try:
                    loc = self.page.locator(sel)
                    if loc.count() > 0:
                        logger.debug(f"[DmSender] 聊天容器已出现: {sel} (等待 {attempt+1} 轮)")
                        self.page.wait_for_timeout(1500)
                        return True
                except Exception:
                    continue

            # 也检查是否有可见的输入元素
            has_input = self.page.evaluate("""() => {
                const els = document.querySelectorAll(
                    'textarea:not(.create-group-notice), [contenteditable="true"], .ql-editor, .ProseMirror'
                );
                for (const el of els) {
                    if (el.offsetParent !== null || el.offsetWidth > 0) return true;
                }
                return false;
            }""")
            if has_input:
                logger.debug(f"[DmSender] 找到可见输入元素 (等待 {attempt+1} 轮)")
                return True

            self.page.wait_for_timeout(2000)

        return False

    def _dump_page_inputs(self):
        """诊断：dump 页面上所有可能的输入元素。"""
        try:
            info = self.page.evaluate("""() => {
                const result = {url: location.href, title: document.title, inputs: [], iframes: []};
                document.querySelectorAll(
                    'textarea, [contenteditable], .ql-editor, .ProseMirror, input[type="text"]'
                ).forEach(el => {
                    result.inputs.push({
                        tag: el.tagName,
                        cls: (el.className || '').toString().substring(0, 120),
                        visible: el.offsetParent !== null || el.offsetWidth > 0,
                        editable: el.contentEditable,
                        rect: {w: el.offsetWidth, h: el.offsetHeight},
                    });
                });
                document.querySelectorAll('iframe').forEach(f => {
                    result.iframes.push({src: (f.src || '').substring(0, 100), rect: {w: f.offsetWidth, h: f.offsetHeight}});
                });
                return result;
            }""")
            logger.info(f"[DmSender] 页面诊断: {json.dumps(info, ensure_ascii=False)}")
        except Exception as e:
            logger.debug(f"[DmSender] 诊断失败: {e}")

    def _find_chat_input(self):
        """定位私信输入框，排除不相关的 textarea。"""
        candidates = [
            "textarea.chat-input:visible",
            ".im-editor [contenteditable='true']",
            ".chat-input[contenteditable='true']",
            "div[contenteditable='true'].chat-input",
            ".textarea-container textarea:not(.create-group-notice):visible",
        ]
        for sel in candidates:
            try:
                loc = self.page.locator(sel).first
                if loc.count() > 0:
                    loc.wait_for(state="visible", timeout=3000)
                    logger.debug(f"[DmSender] 找到输入框: {sel}")
                    return loc
            except Exception:
                continue

        # 兜底：用 JS 找可见的、非 create-group-notice 的输入元素
        el_handle = self.page.evaluate_handle("""() => {
            const textareas = document.querySelectorAll('textarea:not(.create-group-notice)');
            for (const ta of textareas) {
                if (ta.offsetParent !== null && ta.offsetWidth > 0 && ta.offsetHeight > 0) return ta;
            }
            const editables = document.querySelectorAll('[contenteditable="true"]');
            for (const ed of editables) {
                if (ed.offsetParent !== null && ed.offsetWidth > 50 && ed.offsetHeight > 10) return ed;
            }
            return null;
        }""")
        if el_handle:
            as_el = el_handle.as_element()
            if as_el:
                logger.debug("[DmSender] JS 兜底找到输入框")
                return as_el

        raise Exception("未找到可见的聊天输入框")

    def _input_cleared(self) -> bool:
        """发送成功后输入框会被清空；以此验证发送动作确实生效。"""
        try:
            return bool(self.page.evaluate("""() => {
                const els = document.querySelectorAll(
                    'textarea:not(.create-group-notice), [contenteditable="true"]'
                );
                let sawVisible = false;
                for (const el of els) {
                    if (el.offsetParent === null && el.offsetWidth === 0) continue;
                    sawVisible = true;
                    const val = (el.tagName === 'TEXTAREA' ? el.value : el.textContent) || '';
                    if (val.trim().length > 0) return false;
                }
                return sawVisible;
            }"""))
        except Exception:
            return False

    def _check_send_limit(self) -> bool:
        """Check if the page shows a send-limit warning after sending."""
        limit_indicators = [
            "text=你最多发送1条消息",
            "text=发送消息过于频繁",
            "text=对方回复或者关注你后",
        ]
        for selector in limit_indicators:
            try:
                loc = self.page.locator(selector)
                if loc.count() > 0 and loc.is_visible():
                    return True
            except Exception:
                continue
        return False

    def wait_between_sends(self, stop_event: Optional[threading.Event] = None):
        """Random delay between sends to mimic human behavior."""
        delay = random.uniform(self.delay_min, self.delay_max)
        logger.debug(f"[DmSender] 等待 {delay:.1f}s 后继续")
        elapsed = 0.0
        while elapsed < delay:
            if stop_event and stop_event.wait(min(1.0, delay - elapsed)):
                return
            elapsed += 1.0
