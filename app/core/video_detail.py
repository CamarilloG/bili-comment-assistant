"""Fetch supplementary context from a video detail page using Playwright."""

from __future__ import annotations

import os
import json
import threading
from typing import List, Optional

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger()

MAX_COMMENT_CHARS = 500
DEFAULT_MAX_COMMENTS = 10
DEFAULT_MAX_RELATED = 5


def fetch_top_comments(page: Page, url: str, max_count: int = DEFAULT_MAX_COMMENTS, stop_event: Optional[threading.Event] = None) -> List[str]:
    """Navigate to *url*, scroll to load comments, return top-N text contents."""
    try:
        # Check stop signal before navigation
        if stop_event and stop_event.is_set():
            logger.info("[停止响应] 检测到停止信号，中断评论抓取")
            return []

        page.goto(url, wait_until="domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)

        # Check stop signal after navigation
        if stop_event and stop_event.is_set():
            logger.info("[停止响应] 检测到停止信号，中断评论抓取")
            return []

        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4)")
        page.wait_for_timeout(1000)

        # Check stop signal before waiting
        if stop_event and stop_event.is_set():
            logger.info("[停止响应] 检测到停止信号，中断评论抓取")
            return []

        try:
            page.locator("bili-comments").wait_for(state="attached", timeout=5000)
        except Exception:
            logger.debug("[VideoDetail] bili-comments not found, trying legacy selectors")

        # 精确滚动到评论区组件触发懒加载
        try:
            page.evaluate("document.querySelector('bili-comments')?.scrollIntoView({block: 'center', behavior: 'smooth'})")
            page.wait_for_timeout(1500)
        except Exception:
            pass

        # 等待首批评论线程渲染
        for _attempt in range(6):
            _tc = page.locator("bili-comments >>> bili-comment-thread-renderer").count()
            if _tc > 0:
                break
            try:
                _tc = page.evaluate("""() => {
                    const bc = document.querySelector('bili-comments');
                    if (!bc || !bc.shadowRoot) return 0;
                    return bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer').length;
                }""") or 0
                if _tc > 0:
                    break
            except Exception:
                pass
            page.evaluate("window.scrollBy(0, 300)")
            page.wait_for_timeout(1500)

        comments: List[str] = []

        thread_locators = page.locator("bili-comments >>> bili-comment-thread-renderer")
        thread_count = thread_locators.count()

        # JS 兜底获取 thread_count
        if thread_count == 0:
            try:
                thread_count = page.evaluate("""() => {
                    const bc = document.querySelector('bili-comments');
                    if (!bc || !bc.shadowRoot) return 0;
                    return bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer').length;
                }""") or 0
            except Exception:
                pass

        count = min(thread_count, max_count)

        use_js_extract = False
        if thread_locators.count() == 0 and thread_count > 0:
            use_js_extract = True

        for i in range(count):
            if i % 5 == 0 and stop_event and stop_event.is_set():
                logger.info("[停止响应] 检测到停止信号，中断评论抓取")
                return []
            try:
                if use_js_extract:
                    text = page.evaluate("""(idx) => {
                        const bc = document.querySelector('bili-comments');
                        if (!bc || !bc.shadowRoot) return '';
                        const threads = bc.shadowRoot.querySelectorAll('bili-comment-thread-renderer');
                        if (idx >= threads.length) return '';
                        const t = threads[idx];
                        const sr = t.shadowRoot;
                        if (!sr) return '';
                        const renderers = sr.querySelectorAll('bili-comment-renderer');
                        if (renderers.length === 0) return '';
                        const rsr = renderers[0].shadowRoot;
                        if (!rsr) return '';
                        const rich = rsr.querySelector('bili-rich-text');
                        if (!rich) return '';
                        const rrt = rich.shadowRoot;
                        if (!rrt) return rich.textContent.trim();
                        const parts = [];
                        for (const child of rrt.childNodes) {
                            if (child.nodeName === 'STYLE' || child.nodeName === 'LINK') continue;
                            const t = (child.textContent || '').trim();
                            if (t) parts.push(t);
                        }
                        return parts.join(' ');
                    }""", i)
                else:
                    rich = thread_locators.nth(i).locator(">>> bili-rich-text").first
                    text = rich.evaluate("""el => {
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
                if text:
                    comments.append(text[:200])
            except Exception:
                continue

        if not comments:
            fallback = page.locator("#commentapp >>> bili-comment-renderer >>> bili-rich-text")
            legacy_count = fallback.count()
            cnt = min(legacy_count, max_count)
            for i in range(cnt):
                if i % 5 == 0 and stop_event and stop_event.is_set():
                    logger.info("[停止响应] 检测到停止信号，中断评论抓取")
                    return []
                try:
                    text = fallback.nth(i).evaluate("""el => {
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
                    if text:
                        comments.append(text.strip()[:200])
                except Exception:
                    continue

        logger.debug(f"[VideoDetail] Fetched {len(comments)} comments from {url}")
        return comments[:max_count]
    except Exception as e:
        logger.warning(f"[VideoDetail] Failed to fetch comments: {e}")
        return []


def fetch_related_titles(page: Page, max_count: int = DEFAULT_MAX_RELATED) -> List[str]:
    """Extract related-video titles from the current page (call after page is loaded)."""
    titles: List[str] = []
    try:
        cards = page.locator(
            ".rec-list .video-page-card-small, "
            ".recommend-list-v1 .video-page-card-small, "
            ".rec-list-m .video-card"
        )

        page.wait_for_timeout(1000)
        cards_count = cards.count()
        count = min(cards_count, max_count)
        for i in range(count):
            try:
                title_el = cards.nth(i).locator(".title, .info a[title]").first
                text = (title_el.get_attribute("title") or title_el.inner_text(timeout=1000)).strip()
                if text:
                    titles.append(text)
            except Exception:
                continue

        logger.debug(f"[VideoDetail] Fetched {len(titles)} related titles")
    except Exception as e:
        logger.warning(f"[VideoDetail] Failed to fetch related titles: {e}")
    return titles[:max_count]


def truncate_comments(comments: List[str], max_chars: int = MAX_COMMENT_CHARS) -> str:
    """Join comments with numbering, truncating the total to *max_chars*."""
    lines = []
    total = 0
    for idx, c in enumerate(comments, 1):
        line = f"{idx}. {c}"
        if total + len(line) > max_chars:
            break
        lines.append(line)
        total += len(line) + 1
    return "\n".join(lines) if lines else "(无)"
