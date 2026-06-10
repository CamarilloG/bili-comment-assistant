"""Unit tests for core.dm_sender — DmHistory and DmSender."""

import json
import os
import tempfile
import threading
from unittest.mock import MagicMock, patch

import pytest

from core.dm_sender import DmHistory, DmSender, DM_URL_TEMPLATE


# ========== DmHistory ==========

class TestDmHistory:
    def test_empty_file(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h = DmHistory(path)
        assert h.total_sent == 0
        assert h.today_sent == 0
        assert not h.is_sent("123")

    def test_record_and_check(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h = DmHistory(path)

        h.record("100", "UserA", "ok")
        assert h.is_sent("100")
        assert h.total_sent == 1
        assert h.today_sent == 1

    def test_record_failed_not_counted_as_sent(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h = DmHistory(path)

        h.record("200", "UserB", "failed")
        assert h.is_sent("200")
        assert h.total_sent == 0

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h1 = DmHistory(path)
        h1.record("300", "UserC", "ok")

        # Load from same file
        h2 = DmHistory(path)
        assert h2.is_sent("300")
        assert h2.total_sent == 1

    def test_corrupted_file(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        with open(path, "w") as f:
            f.write("not json")

        h = DmHistory(path)
        assert h.total_sent == 0

    def test_multiple_records(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h = DmHistory(path)

        h.record("1", "A", "ok")
        h.record("2", "B", "ok")
        h.record("3", "C", "limited")
        h.record("4", "D", "failed")

        assert h.total_sent == 2
        assert h.is_sent("3")

    def test_overwrite_same_uid(self, tmp_path):
        path = str(tmp_path / "dm_history.json")
        h = DmHistory(path)

        h.record("100", "UserA", "failed")
        assert h.total_sent == 0

        h.record("100", "UserA", "ok")
        assert h.total_sent == 1


# ========== DmSender ==========

class TestDmSender:
    def _make_mock_page(self):
        page = MagicMock()
        page.goto = MagicMock()
        page.wait_for_timeout = MagicMock()
        page.locator = MagicMock()
        return page

    def test_send_dm_stop_before_start(self):
        page = self._make_mock_page()
        sender = DmSender(page)
        stop = threading.Event()
        stop.set()

        result = sender.send_dm("123", "hello", stop_event=stop)
        assert result == "stopped"
        page.goto.assert_not_called()

    def test_send_dm_navigation_failure(self):
        page = self._make_mock_page()
        page.goto.side_effect = Exception("timeout")
        sender = DmSender(page)

        result = sender.send_dm("123", "hello")
        assert result == "failed"

    def test_send_dm_url_format(self):
        page = self._make_mock_page()
        textarea = MagicMock()
        textarea.wait_for = MagicMock()
        textarea.click = MagicMock()
        textarea.fill = MagicMock()
        textarea.type = MagicMock()
        textarea.first = textarea

        send_btn = MagicMock()
        send_btn.wait_for = MagicMock()
        send_btn.click = MagicMock()
        send_btn.first = send_btn

        # No limit indicators
        no_limit = MagicMock()
        no_limit.count.return_value = 0

        call_count = [0]
        def locator_side_effect(sel):
            if "textarea" in sel.lower() or "chat-input" in sel:
                return textarea
            if "button" in sel.lower() or "im-send-btn" in sel:
                return send_btn
            return no_limit

        page.locator = MagicMock(side_effect=locator_side_effect)

        sender = DmSender(page)
        result = sender.send_dm("456", "hi there")

        expected_url = DM_URL_TEMPLATE.format(uid="456")
        page.goto.assert_called_once()
        assert page.goto.call_args[0][0] == expected_url
        assert result == "ok"

    def test_send_dm_detects_limit(self):
        page = self._make_mock_page()
        textarea = MagicMock()
        textarea.wait_for = MagicMock()
        textarea.click = MagicMock()
        textarea.fill = MagicMock()
        textarea.type = MagicMock()
        textarea.first = textarea

        send_btn = MagicMock()
        send_btn.wait_for = MagicMock()
        send_btn.click = MagicMock()
        send_btn.first = send_btn

        limit_locator = MagicMock()
        limit_locator.count.return_value = 1

        def locator_side_effect(sel):
            if "textarea" in sel.lower() or "chat-input" in sel:
                return textarea
            if "button" in sel.lower() or "im-send-btn" in sel:
                return send_btn
            return limit_locator

        page.locator = MagicMock(side_effect=locator_side_effect)

        sender = DmSender(page)
        result = sender.send_dm("789", "hi")
        assert result == "limited"

    def test_delay_range_stored(self):
        page = self._make_mock_page()
        sender = DmSender(page, delay_range=(5.0, 10.0))
        assert sender.delay_min == 5.0
        assert sender.delay_max == 10.0

    def test_wait_between_sends_interrupted(self):
        page = self._make_mock_page()
        sender = DmSender(page, delay_range=(100.0, 200.0))
        stop = threading.Event()

        # Set stop after very short time
        def set_stop():
            import time
            time.sleep(0.1)
            stop.set()

        t = threading.Thread(target=set_stop)
        t.start()
        sender.wait_between_sends(stop_event=stop)
        t.join()
        # Should return quickly, not wait 100+ seconds
