"""Standalone test runner — no pytest needed.

Usage:
    cd app
    python tests/run_tests.py

Runs pure-logic tests for UID extraction and user filtering (no Playwright required).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}")


# ================================================================
print("\n=== _extract_uid_from_href ===")
from core.comment_scraper import _extract_uid_from_href

check("normal url", _extract_uid_from_href("//space.bilibili.com/12345") == "12345")
check("https url", _extract_uid_from_href("https://space.bilibili.com/9999999/") == "9999999")
check("no match", _extract_uid_from_href("https://www.bilibili.com/video/BV1xx") == "")
check("empty string", _extract_uid_from_href("") == "")
check("None input", _extract_uid_from_href(None) == "")
check("uid with path", _extract_uid_from_href("//space.bilibili.com/42/dynamic") == "42")

# ================================================================
print("\n=== regex_filter ===")
from core.user_filter import regex_filter, ai_filter, filter_users

SAMPLE = [
    {"uid": "1", "uname": "Alice", "content": "这个产品哪里买？想买一个"},
    {"uid": "2", "uname": "Bob", "content": "纯路过看看"},
    {"uid": "3", "uname": "Charlie", "content": "求推荐好用的"},
    {"uid": "4", "uname": "Dave", "content": "视频拍的真好"},
    {"uid": "5", "uname": "Eve", "content": "有没有购买链接"},
]

r = regex_filter(SAMPLE, [])
check("empty patterns -> all", len(r) == 5)

r = regex_filter(SAMPLE, ["想买"])
check("single pattern", len(r) == 1 and r[0]["uid"] == "1")

r = regex_filter(SAMPLE, ["想买", "求推荐", "购买"])
check("multi patterns OR", {c["uid"] for c in r} == {"1", "3", "5"})

r = regex_filter(SAMPLE, ["[invalid", "想买"])
check("bad regex ignored", len(r) == 1 and r[0]["uid"] == "1")

r = regex_filter(SAMPLE, ["zzz_not_found"])
check("no match -> empty", len(r) == 0)

r = regex_filter(SAMPLE, [])
check("returns new list", r is not SAMPLE)

# ================================================================
print("\n=== ai_filter (mock) ===")

class MockProvider:
    def __init__(self, response):
        self._response = response
        self.call_count = 0

    def chat(self, system, user):
        self.call_count += 1
        if callable(self._response):
            return self._response(self.call_count)
        return self._response


class MockAI:
    def __init__(self, provider):
        self.provider = provider


check("no ai_manager -> all", len(ai_filter(SAMPLE, "test", None)) == 5)

mgr_none_provider = MockAI(None)
check("no provider -> all", len(ai_filter(SAMPLE, "test", mgr_none_provider)) == 5)

check("empty criteria -> all", len(ai_filter(SAMPLE, "  ", MockAI(MockProvider("x")))) == 5)

p = MockProvider('{"match": true, "reason": "ok"}')
check("ai all match", len(ai_filter(SAMPLE[:2], "test", MockAI(p))) == 2)

p = MockProvider('{"match": false, "reason": "no"}')
check("ai all reject", len(ai_filter(SAMPLE[:2], "test", MockAI(p))) == 0)

p = MockProvider(lambda n: '{"match": true, "reason": "y"}' if n % 2 == 1 else '{"match": false, "reason": "n"}')
r = ai_filter(SAMPLE[:4], "test", MockAI(p))
check("ai mixed", len(r) == 2)

p = MockProvider(None)
check("ai returns None -> preserve", len(ai_filter(SAMPLE[:1], "test", MockAI(p))) == 1)

p = MockProvider("not json at all")
check("ai bad json -> preserve", len(ai_filter(SAMPLE[:1], "test", MockAI(p))) == 1)

p = MockProvider('```json\n{"match": true, "reason": "ok"}\n```')
check("ai markdown json", len(ai_filter(SAMPLE[:1], "test", MockAI(p))) == 1)

p = MockProvider('{"match": true, "reason": "ok"}')
r = ai_filter(SAMPLE, "test", MockAI(p), max_batch=2)
check("max_batch=2", len(r) == 2 and p.call_count == 2)

# ================================================================
print("\n=== filter_users (pipeline) ===")

r = filter_users(SAMPLE)
check("no filters -> all", len(r) == 5)

r = filter_users(SAMPLE, regex_patterns=["想买", "购买"])
check("regex only", {c["uid"] for c in r} == {"1", "5"})

p = MockProvider('{"match": true, "reason": "ok"}')
r = filter_users(SAMPLE, regex_patterns=["想买", "求推荐"], use_ai=True, ai_criteria="test", ai_manager=MockAI(p))
check("regex+ai pipeline", len(r) == 2 and p.call_count == 2)

# ================================================================
print("\n=== DmHistory ===")
import tempfile
import json
from core.dm_sender import DmHistory

with tempfile.TemporaryDirectory() as td:
    path = os.path.join(td, "dm_history.json")
    h = DmHistory(path)
    check("empty history", h.total_sent == 0 and not h.is_sent("1"))

    h.record("1", "A", "ok")
    check("record ok", h.is_sent("1") and h.total_sent == 1)

    h.record("2", "B", "failed")
    check("failed not counted", h.total_sent == 1 and h.is_sent("2"))

    h2 = DmHistory(path)
    check("persistence", h2.is_sent("1") and h2.total_sent == 1)

with tempfile.TemporaryDirectory() as td:
    path = os.path.join(td, "dm_history.json")
    with open(path, "w") as f:
        f.write("corrupt")
    h = DmHistory(path)
    check("corrupted file -> empty", h.total_sent == 0)

# ================================================================
print("\n=== dm_flow stop event ===")
import threading
from core.dm_flow import _get_stop_event, stop_dm_task

ev = _get_stop_event("standalone_test_slot")
check("event created", isinstance(ev, threading.Event) and not ev.is_set())

ev2 = _get_stop_event("standalone_test_slot")
check("same event returned", ev is ev2)

ev.clear()
stop_dm_task("standalone_test_slot")
check("stop sets event", ev.is_set())

# ================================================================
print(f"\n{'='*40}")
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
if failed:
    print("SOME TESTS FAILED!")
    sys.exit(1)
else:
    print("ALL TESTS PASSED!")
    sys.exit(0)
