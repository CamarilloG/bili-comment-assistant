"""Fetch supplementary context from a video detail page using Playwright."""

from __future__ import annotations

import os
import json
from typing import List

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger()

MAX_COMMENT_CHARS = 500
DEFAULT_MAX_COMMENTS = 10
DEFAULT_MAX_RELATED = 5


def _debug_log(payload: dict) -> None:
    """写入本次调试会话的评论/推荐抓取日志。"""
    try:
        payload.setdefault("sessionId", "829736")
        import time as _t
        payload.setdefault("timestamp", int(_t.time() * 1000))
        log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "debug-829736.log"))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def fetch_top_comments(page: Page, url: str, max_count: int = DEFAULT_MAX_COMMENTS) -> List[str]:
    """Navigate to *url*, scroll to load comments, return top-N text contents."""
    _debug_log({
        "location": "video_detail.py:fetch_top_comments:entry",
        "message": "fetch_top_comments start",
        "hypothesisId": "C1",
        "data": {"url": url[:120], "max_count": max_count},
    })
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(1500)

        page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.4)")
        page.wait_for_timeout(2000)

        try:
            page.locator("bili-comments").wait_for(state="attached", timeout=8000)
        except Exception:
            logger.debug("[VideoDetail] bili-comments not found, trying legacy selectors")

        comments: List[str] = []

        # 通过 Playwright 的 >>> 语法穿透 bili-comments 与 bili-comment-thread-renderer 的 Shadow DOM
        # 1) 优先从 bili-comments 下的顶层评论线程抓取
        thread_locators = page.locator("bili-comments >>> bili-comment-thread-renderer")
        thread_count = thread_locators.count()
        _debug_log({
            "location": "video_detail.py:fetch_top_comments:threads",
            "message": "comment threads count",
            "hypothesisId": "C2",
            "data": {"url": url[:120], "thread_count": thread_count},
        })
        count = min(thread_count, max_count)
        for i in range(count):
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
            _debug_log({
                "location": "video_detail.py:fetch_top_comments:legacy",
                "message": "fallback rich-text count",
                "hypothesisId": "C3",
                "data": {"url": url[:120], "legacy_count": legacy_count},
            })
            cnt = min(legacy_count, max_count)
            for i in range(cnt):
                try:
                    text = fallback.nth(i).inner_text(timeout=2000).strip()
                    if text:
                        comments.append(text[:200])
                except Exception:
                    continue

        logger.debug(f"[VideoDetail] Fetched {len(comments)} comments from {url}")
        _debug_log({
            "location": "video_detail.py:fetch_top_comments:exit",
            "message": "fetch_top_comments done",
            "hypothesisId": "C4",
            "data": {"url": url[:120], "comments_len": len(comments)},
        })
        return comments[:max_count]
    except Exception as e:
        logger.warning(f"[VideoDetail] Failed to fetch comments: {e}")
        _debug_log({
            "location": "video_detail.py:fetch_top_comments:error",
            "message": "fetch_top_comments error",
            "hypothesisId": "C5",
            "data": {"url": url[:120], "error": str(e)},
        })
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
        _debug_log({
            "location": "video_detail.py:fetch_related_titles:cards",
            "message": "related cards count",
            "hypothesisId": "R1",
            "data": {"cards_count": cards_count},
        })
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
        _debug_log({
            "location": "video_detail.py:fetch_related_titles:exit",
            "message": "fetch_related_titles done",
            "hypothesisId": "R2",
            "data": {"titles_len": len(titles)},
        })
    except Exception as e:
        logger.warning(f"[VideoDetail] Failed to fetch related titles: {e}")
        _debug_log({
            "location": "video_detail.py:fetch_related_titles:error",
            "message": "fetch_related_titles error",
            "hypothesisId": "R3",
            "data": {"error": str(e)},
        })
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
