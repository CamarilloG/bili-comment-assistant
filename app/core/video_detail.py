"""Fetch supplementary context from a video detail page using Playwright."""

from __future__ import annotations

from typing import List

from playwright.sync_api import Page

from utils.logger import get_logger

logger = get_logger()

MAX_COMMENT_CHARS = 500
DEFAULT_MAX_COMMENTS = 10
DEFAULT_MAX_RELATED = 5


def fetch_top_comments(page: Page, url: str, max_count: int = DEFAULT_MAX_COMMENTS) -> List[str]:
    """Navigate to *url*, scroll to load comments, return top-N text contents."""
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

        thread_locators = page.locator("bili-comments bili-comment-thread-renderer")
        count = min(thread_locators.count(), max_count)
        for i in range(count):
            try:
                rich = thread_locators.nth(i).locator("bili-rich-text").first
                text = rich.inner_text(timeout=2000).strip()
                if text:
                    comments.append(text[:200])
            except Exception:
                continue

        if not comments:
            legacy = page.locator(".reply-content .reply-content-container .reply-content")
            cnt = min(legacy.count(), max_count)
            for i in range(cnt):
                try:
                    text = legacy.nth(i).inner_text(timeout=2000).strip()
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
        count = min(cards.count(), max_count)
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
