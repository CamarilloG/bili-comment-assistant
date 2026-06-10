"""Shared fixtures and module-level mocks for DM module tests.

Playwright depends on greenlet which may fail to load (missing VC++ runtime / embedded Python).
We mock the entire playwright module tree in sys.modules BEFORE any core module is imported,
so tests can run without a real Playwright installation.
"""

import sys
import os
import types
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# 1. Ensure app/ is on sys.path
# ---------------------------------------------------------------------------
_app_dir = os.path.join(os.path.dirname(__file__), "..")
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

# ---------------------------------------------------------------------------
# 2. Mock playwright module tree before anything imports it
# ---------------------------------------------------------------------------

class _AttrModule(types.ModuleType):
    """Module that returns MagicMock for any missing attribute (Page, BrowserContext, etc.)."""
    def __getattr__(self, name):
        return MagicMock

_playwright_modules = [
    "playwright",
    "playwright.sync_api",
    "playwright.async_api",
    "playwright._impl",
    "playwright._impl._connection",
    "playwright._impl._greenlets",
    "playwright._impl._assertions",
    "greenlet",
]

for _mod_name in _playwright_modules:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = _AttrModule(_mod_name)
