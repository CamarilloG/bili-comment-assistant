"""Unit tests for core.comment_scraper — UID extraction and scrape logic."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from core.comment_scraper import _extract_uid_from_href, CommentScraper


# ========== _extract_uid_from_href ==========

class TestExtractUid:
    def test_normal_url(self):
        assert _extract_uid_from_href("//space.bilibili.com/12345") == "12345"

    def test_https_url(self):
        assert _extract_uid_from_href("https://space.bilibili.com/9999999/") == "9999999"

    def test_no_match(self):
        assert _extract_uid_from_href("https://www.bilibili.com/video/BV1xx") == ""

    def test_empty(self):
        assert _extract_uid_from_href("") == ""

    def test_none(self):
        assert _extract_uid_from_href(None) == ""

    def test_uid_with_path_suffix(self):
        assert _extract_uid_from_href("//space.bilibili.com/42/dynamic") == "42"


# ========== CommentScraper ==========

class TestCommentScraper:
    def _make_mock_page(self):
        page = MagicMock()
        page.goto = MagicMock()
        page.wait_for_timeout = MagicMock()
        page.evaluate = MagicMock()
        page.locator = MagicMock()
        return page

    def test_returns_empty_on_stop_event_before_start(self):
        page = self._make_mock_page()
        scraper = CommentScraper(page)
        stop = threading.Event()
        stop.set()

        result = scraper.scrape_comments("https://bilibili.com/video/BV1test", stop_event=stop)
        assert result == []
        page.goto.assert_not_called()

    def test_returns_empty_on_navigation_failure(self):
        page = self._make_mock_page()
        page.goto.side_effect = Exception("Timeout")
        scraper = CommentScraper(page)

        result = scraper.scrape_comments("https://bilibili.com/video/BV1test")
        assert result == []

    def test_returns_empty_when_bili_comments_not_found(self):
        page = self._make_mock_page()
        bili_comments_locator = MagicMock()
        bili_comments_locator.wait_for = MagicMock(side_effect=Exception("not found"))
        page.locator.return_value = bili_comments_locator

        scraper = CommentScraper(page)
        result = scraper.scrape_comments("https://bilibili.com/video/BV1test")
        assert result == []

    def test_extract_comment_info_returns_none_when_no_data(self):
        page = self._make_mock_page()
        scraper = CommentScraper(page)

        thread_el = MagicMock()
        # user_link locator returns 0 count
        link_locator = MagicMock()
        link_locator.count.return_value = 0
        link_locator.first = link_locator

        # rich text locator returns 0 count
        rich_locator = MagicMock()
        rich_locator.count.return_value = 0
        rich_locator.first = rich_locator

        thread_el.locator = MagicMock(side_effect=lambda sel: rich_locator if "rich-text" in sel else link_locator)

        result = scraper._extract_comment_info(thread_el)
        assert result is None

    def test_extract_comment_info_happy_path(self):
        page = self._make_mock_page()
        scraper = CommentScraper(page)

        thread_el = MagicMock()

        user_link = MagicMock()
        user_link.count.return_value = 1
        user_link.get_attribute.return_value = "//space.bilibili.com/12345"
        user_link.inner_text.return_value = "TestUser"
        user_link.first = user_link

        rich_text = MagicMock()
        rich_text.count.return_value = 1
        rich_text.inner_text.return_value = "这个视频真不错"
        rich_text.first = rich_text

        def locator_side_effect(sel):
            if "space.bilibili.com" in sel:
                return user_link
            if "rich-text" in sel:
                return rich_text
            m = MagicMock()
            m.count.return_value = 0
            m.first = m
            return m

        thread_el.locator = MagicMock(side_effect=locator_side_effect)

        result = scraper._extract_comment_info(thread_el)
        assert result is not None
        assert result["uid"] == "12345"
        assert result["uname"] == "TestUser"
        assert result["content"] == "这个视频真不错"

    def test_deduplicates_by_uid(self):
        """Scrape loop should skip duplicate UIDs."""
        page = self._make_mock_page()

        # Mock bili-comments wait_for
        bili_comments = MagicMock()
        bili_comments.wait_for = MagicMock()

        # Create thread locators that return the same UID twice
        threads_locator = MagicMock()
        threads_locator.count.side_effect = [2, 2, 2, 2]  # stale 3 times then break

        user_link = MagicMock()
        user_link.count.return_value = 1
        user_link.get_attribute.return_value = "//space.bilibili.com/100"
        user_link.inner_text.return_value = "SameUser"
        user_link.first = user_link

        rich_text = MagicMock()
        rich_text.count.return_value = 1
        rich_text.inner_text.return_value = "comment"
        rich_text.first = rich_text

        thread_el = MagicMock()
        def thread_locator(sel):
            if "space.bilibili.com" in sel:
                return user_link
            if "rich-text" in sel:
                return rich_text
            m = MagicMock()
            m.count.return_value = 0
            m.first = m
            return m
        thread_el.locator = MagicMock(side_effect=thread_locator)

        threads_locator.nth = MagicMock(return_value=thread_el)

        def page_locator(sel):
            if sel == "bili-comments":
                return bili_comments
            return threads_locator

        page.locator = MagicMock(side_effect=page_locator)

        scraper = CommentScraper(page)
        result = scraper.scrape_comments("https://bilibili.com/video/BV1test")

        # Should only have 1 unique UID despite 2 threads
        assert len(result) <= 1
