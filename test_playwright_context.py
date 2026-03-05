"""
测试 Playwright 上下文管理器
"""
from playwright.sync_api import sync_playwright
import sys
import os

# 设置 UTF-8 编码
if os.name == 'nt':
    import ctypes
    ctypes.windll.kernel32.SetConsoleOutputCP(65001)

print("=" * 60)
print("Test Playwright Context Manager")
print("=" * 60)
print()

print("[1/3] Test sync_playwright() import...")
try:
    print(f"  sync_playwright: {sync_playwright}")
    print("  OK - Import success")
except Exception as e:
    print(f"  ERROR - Import failed: {e}")
    sys.exit(1)

print()

print("[2/3] Test sync_playwright() context manager...")
try:
    print("  Entering: with sync_playwright() as p:")
    with sync_playwright() as p:
        print(f"    p = {p}")
        print(f"    p.chromium = {p.chromium}")
        print("  OK - Context manager works")
except Exception as e:
    print(f"  ERROR - Context manager failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

print("[3/3] Test browser launch...")
try:
    with sync_playwright() as p:
        print("  Launching browser...")
        browser = p.chromium.launch(headless=True)
        print(f"    browser = {browser}")
        print("  OK - Browser launched")
        browser.close()
        print("  OK - Browser closed")
except Exception as e:
    print(f"  ERROR - Browser launch failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()
print("=" * 60)
print("All tests passed")
print("=" * 60)
