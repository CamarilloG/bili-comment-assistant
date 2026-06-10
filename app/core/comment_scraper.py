"""Scrape comment section via Playwright DOM to extract user UIDs, names and comment text."""

from __future__ import annotations

import re
import threading
from typing import Dict, List, Optional

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger()

DEFAULT_MAX_COMMENTS = 200
SCROLL_PAUSE_MS = 2000
MAX_SCROLL_ATTEMPTS = 40
STALE_LIMIT = 6


def _extract_uid_from_href(href: str) -> str:
    """Extract numeric UID from a space.bilibili.com link."""
    m = re.search(r"space\.bilibili\.com/(\d+)", href or "")
    return m.group(1) if m else ""


class CommentScraper:
    def __init__(self, page: Page):
        self.page = page

    def scrape_comments(
        self,
        url: str,
        max_count: int = DEFAULT_MAX_COMMENTS,
        stop_event: Optional[threading.Event] = None,
    ) -> List[Dict[str, str]]:
        if stop_event and stop_event.is_set():
            return []

        # ---------- 1. 导航 ----------
        try:
            self.page.goto(url, wait_until="domcontentloaded", timeout=20000)
            self.page.wait_for_timeout(2000)
        except Exception as e:
            logger.error(f"[CommentScraper] 导航到视频页失败: {e}")
            return []

        if stop_event and stop_event.is_set():
            return []

        # ---------- 2. 滚动到评论区触发懒加载 ----------
        if not self._scroll_to_comment_area():
            logger.warning("[CommentScraper] 未能定位到评论区")
            return []

        if stop_event and stop_event.is_set():
            return []

        # ---------- 3. 等待评论线程渲染 ----------
        self._wait_for_first_thread()
        self._dump_thread_structure()

        # ---------- 4. 循环滚动收集评论 ----------
        results: List[Dict[str, str]] = []
        seen_uids: set = set()
        prev_count = 0
        stale_rounds = 0

        for scroll_round in range(MAX_SCROLL_ATTEMPTS):
            if stop_event and stop_event.is_set():
                break

            thread_count = self._get_thread_count()

            if scroll_round == 0 and thread_count > 0:
                logger.debug(f"[CommentScraper] 首轮提取: thread_count={thread_count}")

            for i in range(prev_count, thread_count):
                if len(results) >= max_count:
                    break
                if i % 10 == 0 and stop_event and stop_event.is_set():
                    break
                try:
                    info = self._extract_comment_at(i)
                    if i < 3:
                        logger.debug(f"[CommentScraper] 提取第{i}条: {info}")
                    if info and info["uid"] and info["uid"] not in seen_uids:
                        seen_uids.add(info["uid"])
                        results.append(info)
                except Exception as e:
                    if i < 3:
                        logger.debug(f"[CommentScraper] 提取第{i}条异常: {e}")
                    continue

            if len(results) >= max_count:
                break

            if thread_count == prev_count:
                stale_rounds += 1
                if stale_rounds >= STALE_LIMIT:
                    break
            else:
                stale_rounds = 0

            prev_count = thread_count

            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            self.page.wait_for_timeout(SCROLL_PAUSE_MS)

        logger.info(f"[CommentScraper] 从 {url} 抓取到 {len(results)} 条用户评论")
        return results

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    def _scroll_to_comment_area(self) -> bool:
        """精确滚动到评论区组件，触发懒加载。"""
        anchors = ["bili-comments", "#commentapp", "#comment"]
        for anchor in anchors:
            try:
                loc = self.page.locator(anchor)
                if loc.count() > 0:
                    self.page.evaluate(
                        f"document.querySelector('{anchor}')"
                        ".scrollIntoView({block: 'center', behavior: 'smooth'})"
                    )
                    self.page.wait_for_timeout(1500)
                    logger.debug(f"[CommentScraper] 已滚动到 {anchor}")
                    break
            except Exception:
                continue
        else:
            self.page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
            self.page.wait_for_timeout(1500)

        try:
            self.page.locator("bili-comments").wait_for(state="attached", timeout=10000)
            return True
        except Exception:
            try:
                self.page.locator("#commentapp").wait_for(state="attached", timeout=5000)
                return True
            except Exception:
                return False

    def _wait_for_first_thread(self) -> None:
        """等待至少一条评论线程渲染出来。"""
        for attempt in range(8):
            count = self._get_thread_count()
            if count > 0:
                logger.debug(f"[CommentScraper] 首批评论已渲染，共 {count} 条 (等待 {attempt+1} 轮)")
                return
            self.page.evaluate("window.scrollBy(0, 300)")
            self.page.wait_for_timeout(1500)
        logger.debug("[CommentScraper] 等待首批评论超时，将继续尝试滚动")

    def _get_thread_count(self) -> int:
        """获取当前页面上可见的评论线程数量，尝试多种选择器。"""
        selectors = [
            "bili-comments >>> bili-comment-thread-renderer",
            "#commentapp >>> bili-comment-thread-renderer",
        ]
        for sel in selectors:
            try:
                count = self.page.locator(sel).count()
                if count > 0:
                    return count
            except Exception:
                continue

        try:
            count = self.page.evaluate("""() => {
                const bc = document.querySelector('bili-comments');
                if (!bc || !bc.shadowRoot) return 0;
                return bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer').length;
            }""")
            if count and count > 0:
                return count
        except Exception:
            pass

        return 0

    def _extract_comment_at(self, index: int) -> Optional[Dict[str, str]]:
        """从第 index 个评论线程提取用户信息。"""
        thread = None
        for sel in [
            "bili-comments >>> bili-comment-thread-renderer",
            "#commentapp >>> bili-comment-thread-renderer",
        ]:
            try:
                loc = self.page.locator(sel)
                if loc.count() > index:
                    thread = loc.nth(index)
                    break
            except Exception:
                continue

        if thread is not None:
            return self._extract_comment_info(thread)

        return self._extract_comment_info_js(index)

    def _dump_thread_structure(self) -> None:
        """诊断：dump 第一个评论线程的 DOM 结构到日志。"""
        try:
            info = self.page.evaluate("""() => {
                const bc = document.querySelector('bili-comments');
                if (!bc) return 'bili-comments not found';
                const bcsr = bc.shadowRoot;
                if (!bcsr) return 'bili-comments has no shadowRoot';

                const threads = bcsr.querySelectorAll('bili-comment-thread-renderer');
                if (threads.length === 0) return 'no threads in bili-comments shadowRoot';

                const t = threads[0];
                const result = {threadTag: t.tagName, hasSR: !!t.shadowRoot, childTags: []};

                function describeEl(root, depth, maxDepth) {
                    if (depth > maxDepth) return;
                    const children = root.children || [];
                    for (let i = 0; i < Math.min(children.length, 10); i++) {
                        const c = children[i];
                        const desc = {tag: c.tagName, hasSR: !!c.shadowRoot};
                        if (c.className) desc.cls = (typeof c.className === 'string' ? c.className : '').substring(0, 80);
                        if (c.href) desc.href = c.href.substring(0, 80);
                        result.childTags.push('[' + depth + '] ' + JSON.stringify(desc));
                        if (c.shadowRoot) {
                            result.childTags.push('[' + depth + '.sr] entering shadowRoot of ' + c.tagName);
                            describeEl(c.shadowRoot, depth + 1, maxDepth);
                        }
                        describeEl(c, depth + 1, maxDepth);
                    }
                }

                if (t.shadowRoot) {
                    describeEl(t.shadowRoot, 1, 4);
                } else {
                    describeEl(t, 1, 4);
                }
                return result;
            }""")
            logger.debug(f"[CommentScraper] 首条评论线程 DOM 结构: {info}")
        except Exception as e:
            logger.debug(f"[CommentScraper] dump 结构失败: {e}")

    def _extract_comment_info_js(self, index: int) -> Optional[Dict[str, str]]:
        """通过 JS 递归遍历 Shadow DOM 提取评论信息（兜底方案）。"""
        try:
            result = self.page.evaluate("""(idx) => {
                const bc = document.querySelector('bili-comments');
                if (!bc || !bc.shadowRoot) return null;
                const threads = bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer');
                if (idx >= threads.length) return null;
                const thread = threads[idx];

                function deepQueryAll(root, selector) {
                    let results = [];
                    try { results = Array.from(root.querySelectorAll(selector)); } catch(e) {}
                    const allEls = root.querySelectorAll('*');
                    for (const el of allEls) {
                        if (el.shadowRoot) {
                            results = results.concat(deepQueryAll(el.shadowRoot, selector));
                        }
                    }
                    return results;
                }

                let uid = '', uname = '', content = '';
                const searchRoot = thread.shadowRoot || thread;

                // 1) 提取 UID：从 a[href*=space.bilibili.com]
                const userLinks = deepQueryAll(searchRoot, 'a[href*="space.bilibili.com"]');
                if (userLinks.length > 0) {
                    const href = userLinks[0].getAttribute('href') || '';
                    const m = href.match(/space\\.bilibili\\.com\\/(\\d+)/);
                    if (m) uid = m[1];
                }

                // 2) 提取用户名：优先 .user-name，其次 a 标签文字
                const nameEls = deepQueryAll(searchRoot, '.user-name');
                if (nameEls.length > 0) {
                    uname = nameEls[0].textContent.trim();
                }
                if (!uname && userLinks.length > 0) {
                    uname = userLinks[0].textContent.trim();
                }

                // 3) 提取评论内容：从 bili-rich-text 的 shadowRoot 中读取，跳过 <style>
                const richTexts = deepQueryAll(searchRoot, 'bili-rich-text');
                if (richTexts.length > 0) {
                    const rich = richTexts[0];
                    const rsr = rich.shadowRoot;
                    if (rsr) {
                        const parts = [];
                        for (const child of rsr.childNodes) {
                            if (child.nodeName === 'STYLE' || child.nodeName === 'LINK') continue;
                            const t = (child.textContent || '').trim();
                            if (t) parts.push(t);
                        }
                        content = parts.join(' ').trim();
                    }
                    if (!content) {
                        content = rich.textContent.trim();
                    }
                }

                if (!content) {
                    const replyEls = deepQueryAll(searchRoot, '.reply-content, .root-reply-content, .text-con');
                    if (replyEls.length > 0) {
                        content = replyEls[0].textContent.trim();
                    }
                }

                if (!uid && !content) return null;
                return {uid: uid, uname: uname, content: content.substring(0, 500)};
            }""", index)
            if not isinstance(result, dict):
                return None
            uid = result.get("uid")
            uname = result.get("uname")
            content = result.get("content")
            if not isinstance(uid, str) or not isinstance(uname, str) or not isinstance(content, str):
                return None
            return {"uid": uid, "uname": uname, "content": content}
        except Exception as e:
            if index == 0:
                logger.debug(f"[CommentScraper] JS 提取第0条失败: {e}")
            return None

    def _extract_comment_info(self, thread) -> Optional[Dict[str, str]]:
        """Extract uid, uname, content from a single comment thread element."""
        uid = ""
        uname = ""
        content = ""

        try:
            user_link = thread.locator(">>> a[href*='space.bilibili.com']").first
            if user_link.count() > 0:
                href = user_link.get_attribute("href", timeout=3000) or ""
                uid = _extract_uid_from_href(href)
        except Exception:
            pass

        try:
            name_el = thread.locator(">>> .user-name").first
            if name_el.count() > 0:
                uname = name_el.inner_text(timeout=3000).strip()
        except Exception:
            pass
        if not uname:
            try:
                uname = user_link.inner_text(timeout=3000).strip()
            except Exception:
                pass

        try:
            rich = thread.locator(">>> bili-rich-text").first
            if rich.count() > 0:
                raw = rich.evaluate("""el => {
                    const sr = el.shadowRoot;
                    if (!sr) return el.textContent || '';
                    const parts = [];
                    for (const child of sr.childNodes) {
                        if (child.nodeName === 'STYLE' || child.nodeName === 'LINK') continue;
                        const t = (child.textContent || '').trim();
                        if (t) parts.push(t);
                    }
                    return parts.join(' ');
                }""")
                if isinstance(raw, str):
                    content = raw.strip()[:500]
                if not content:
                    content = rich.inner_text(timeout=3000).strip()[:500]
        except Exception:
            pass

        if not uid and not content:
            return None

        return {"uid": uid, "uname": uname, "content": content}
