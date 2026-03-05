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

        comments: List[str] = []

        # 通过 Playwright 的 >>> 语法穿透 bili-comments 与 bili-comment-thread-renderer 的 Shadow DOM
        # 1) 优先从 bili-comments 下的顶层评论线程抓取
        thread_locators = page.locator("bili-comments >>> bili-comment-thread-renderer")
        thread_count = thread_locators.count()
        count = min(thread_count, max_count)
        for i in range(count):
            # Check stop signal every 5 iterations
            if i % 5 == 0 and stop_event and stop_event.is_set():
                logger.info("[停止响应] 检测到停止信号，中断评论抓取")
                return []
            try:
                rich = thread_locators.nth(i).locator(">>> bili-rich-text").first
                text = rich.inner_text(timeout=2000).strip()
                if text:
                    comments.append(text[:200])
            except Exception:
                continue

        # 2) 若仍未抓到，尝试直接在 commentapp 树下抓取任意顶层评论文本
        if not comments:
            fallback = page.locator("#commentapp >>> bili-comment-renderer >>> bili-rich-text")
            legacy_count = fallback.count()
            cnt = min(legacy_count, max_count)
            for i in range(cnt):
                # Check stop signal every 5 iterations
                if i % 5 == 0 and stop_event and stop_event.is_set():
                    logger.info("[停止响应] 检测到停止信号，中断评论抓取")
                    return []
                try:
                    text = fallback.nth(i).inner_text(timeout=2000).strip()
                    if text:
                        comments.append(text[:200])
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
