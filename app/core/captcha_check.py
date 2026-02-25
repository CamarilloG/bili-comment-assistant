"""Shared captcha detection for any page (comment, warmup, etc.)."""
from playwright.sync_api import Page
from core.selectors import BilibiliSelectors


def check_captcha_on_page(page: Page) -> bool:
    """Return True if captcha/risk-control popup is present on the given page."""
    try:
        selector = BilibiliSelectors.COMMENT["captcha"]
        return page.locator(selector).count() > 0
    except Exception:
        return False
