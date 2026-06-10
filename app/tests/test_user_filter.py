"""Unit tests for core.user_filter — regex and AI filtering."""

from unittest.mock import MagicMock

import pytest

from core.user_filter import regex_filter, ai_filter, filter_users


SAMPLE_COMMENTS = [
    {"uid": "1", "uname": "Alice", "content": "这个产品哪里买？想买一个"},
    {"uid": "2", "uname": "Bob", "content": "纯路过看看"},
    {"uid": "3", "uname": "Charlie", "content": "求推荐好用的"},
    {"uid": "4", "uname": "Dave", "content": "视频拍的真好"},
    {"uid": "5", "uname": "Eve", "content": "有没有购买链接"},
]


# ========== regex_filter ==========

class TestRegexFilter:
    def test_empty_patterns_returns_all(self):
        result = regex_filter(SAMPLE_COMMENTS, [])
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_single_pattern(self):
        result = regex_filter(SAMPLE_COMMENTS, ["想买"])
        assert len(result) == 1
        assert result[0]["uid"] == "1"

    def test_multiple_patterns_or_logic(self):
        result = regex_filter(SAMPLE_COMMENTS, ["想买", "求推荐", "购买"])
        uids = {c["uid"] for c in result}
        assert uids == {"1", "3", "5"}

    def test_case_insensitive(self):
        comments = [{"uid": "1", "uname": "A", "content": "Buy this NOW"}]
        result = regex_filter(comments, ["buy"])
        assert len(result) == 1

    def test_invalid_regex_ignored(self):
        result = regex_filter(SAMPLE_COMMENTS, ["[invalid", "想买"])
        assert len(result) == 1
        assert result[0]["uid"] == "1"

    def test_all_invalid_regex_returns_all(self):
        result = regex_filter(SAMPLE_COMMENTS, ["[bad1", "[bad2"])
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_no_match_returns_empty(self):
        result = regex_filter(SAMPLE_COMMENTS, ["完全不存在的关键词xyz"])
        assert result == []

    def test_empty_content_field(self):
        comments = [{"uid": "1", "uname": "A", "content": ""}]
        result = regex_filter(comments, ["test"])
        assert result == []

    def test_returns_new_list(self):
        result = regex_filter(SAMPLE_COMMENTS, [])
        assert result is not SAMPLE_COMMENTS


# ========== ai_filter ==========

class TestAiFilter:
    def test_no_ai_manager_returns_all(self):
        result = ai_filter(SAMPLE_COMMENTS, "test criteria", None)
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_no_provider_returns_all(self):
        mgr = MagicMock()
        mgr.provider = None
        result = ai_filter(SAMPLE_COMMENTS, "test", mgr)
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_empty_criteria_returns_all(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        result = ai_filter(SAMPLE_COMMENTS, "  ", mgr)
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_ai_match(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '{"match": true, "reason": "has intent"}'

        result = ai_filter(SAMPLE_COMMENTS[:2], "购买意向", mgr)
        assert len(result) == 2

    def test_ai_reject(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '{"match": false, "reason": "no intent"}'

        result = ai_filter(SAMPLE_COMMENTS[:2], "购买意向", mgr)
        assert len(result) == 0

    def test_ai_mixed_results(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.side_effect = [
            '{"match": true, "reason": "yes"}',
            '{"match": false, "reason": "no"}',
            '{"match": true, "reason": "yes"}',
        ]

        result = ai_filter(SAMPLE_COMMENTS[:3], "购买意向", mgr)
        assert len(result) == 2
        assert result[0]["uid"] == "1"
        assert result[1]["uid"] == "3"

    def test_ai_returns_none_preserves_comment(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = None

        result = ai_filter(SAMPLE_COMMENTS[:1], "test", mgr)
        assert len(result) == 1

    def test_ai_json_parse_error_preserves(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = "not valid json"

        result = ai_filter(SAMPLE_COMMENTS[:1], "test", mgr)
        assert len(result) == 1

    def test_ai_exception_preserves(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.side_effect = Exception("API down")

        result = ai_filter(SAMPLE_COMMENTS[:1], "test", mgr)
        assert len(result) == 1

    def test_max_batch_limits(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '{"match": true, "reason": "ok"}'

        result = ai_filter(SAMPLE_COMMENTS, "test", mgr, max_batch=2)
        # Only first 2 comments processed
        assert len(result) == 2
        assert mgr.provider.chat.call_count == 2

    def test_ai_handles_markdown_json(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '```json\n{"match": true, "reason": "ok"}\n```'

        result = ai_filter(SAMPLE_COMMENTS[:1], "test", mgr)
        assert len(result) == 1


# ========== filter_users (pipeline) ==========

class TestFilterUsers:
    def test_no_filters_returns_all(self):
        result = filter_users(SAMPLE_COMMENTS)
        assert len(result) == len(SAMPLE_COMMENTS)

    def test_regex_only(self):
        result = filter_users(SAMPLE_COMMENTS, regex_patterns=["想买", "购买"])
        uids = {c["uid"] for c in result}
        assert uids == {"1", "5"}

    def test_ai_only(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '{"match": false, "reason": "no"}'

        result = filter_users(
            SAMPLE_COMMENTS[:2],
            use_ai=True,
            ai_criteria="购买意向",
            ai_manager=mgr,
        )
        assert len(result) == 0

    def test_pipeline_regex_then_ai(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()
        mgr.provider.chat.return_value = '{"match": true, "reason": "yes"}'

        result = filter_users(
            SAMPLE_COMMENTS,
            regex_patterns=["想买", "求推荐"],
            use_ai=True,
            ai_criteria="购买意向",
            ai_manager=mgr,
        )
        # regex hits: uid 1,3 → AI keeps both
        assert len(result) == 2
        # AI only called for regex survivors
        assert mgr.provider.chat.call_count == 2

    def test_ai_skipped_when_no_criteria(self):
        mgr = MagicMock()
        mgr.provider = MagicMock()

        result = filter_users(
            SAMPLE_COMMENTS,
            use_ai=True,
            ai_criteria="",
            ai_manager=mgr,
        )
        assert len(result) == len(SAMPLE_COMMENTS)
        mgr.provider.chat.assert_not_called()

    def test_returns_new_list(self):
        result = filter_users(SAMPLE_COMMENTS)
        assert result is not SAMPLE_COMMENTS
