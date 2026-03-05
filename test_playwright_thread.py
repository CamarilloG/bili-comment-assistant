"""
测试修复后的 Playwright 启动
模拟 uvicorn 异步环境中的调用
"""
import sys
import os
import threading

# 添加 app 目录到路径
app_dir = os.path.join(os.getcwd(), 'app')
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

print("=" * 60)
print("Test Playwright in Thread (simulating uvicorn)")
print("=" * 60)
print()

def test_main():
    """模拟 main.py 中的启动流程"""
    from playwright.sync_api import sync_playwright
    import asyncio

    print("[Thread] Starting test...")

    # Python 3.13 兼容性
    if sys.platform == 'win32' and sys.version_info >= (3, 13):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            print("[Thread] Set WindowsSelectorEventLoopPolicy")
        except Exception as e:
            print(f"[Thread] Failed to set event loop policy: {e}")

    try:
        print("[Thread] Calling sync_playwright().start()...")
        pw = sync_playwright().start()
        print(f"[Thread] Playwright started: {pw}")

        print("[Thread] Launching browser...")
        browser = pw.chromium.launch(headless=True)
        print(f"[Thread] Browser launched: {browser}")

        print("[Thread] Closing browser...")
        browser.close()

        print("[Thread] Stopping Playwright...")
        pw.stop()

        print("[Thread] SUCCESS - All steps completed")
        return True

    except Exception as e:
        print(f"[Thread] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

# 在线程中运行（模拟 uvicorn 的 daemon thread）
print("[Main] Creating thread...")
thread = threading.Thread(target=test_main, daemon=True)
thread.start()

print("[Main] Waiting for thread...")
thread.join(timeout=30)

if thread.is_alive():
    print("[Main] ERROR - Thread timed out")
    sys.exit(1)
else:
    print("[Main] Thread completed")
    print()
    print("=" * 60)
    print("Test completed successfully")
    print("=" * 60)
