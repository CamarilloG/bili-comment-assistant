# 验证码监听器 - 智能监听，定时自动停止

import time
from typing import Optional, Callable
from playwright.sync_api import Page

try:
    from douyin.logger import get_douyin_logger

    logger = get_douyin_logger()
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class CaptchaMonitor:
    """验证码监听器 - 使用定时器而非后台线程，避免线程冲突"""

    def __init__(
        self,
        page: Page,
        callback: Optional[Callable[[str], None]] = None,
        auto_stop_seconds: int = 10,
    ):
        """
        初始化验证码监听器

        :param page: Playwright Page 对象
        :param callback: 回调函数，用于通知GUI
        :param auto_stop_seconds: 自动停止监听的秒数（默认10秒）
        """
        self.page = page
        self.callback = callback
        self.auto_stop_seconds = auto_stop_seconds
        self.is_monitoring = False
        self.start_time: float = 0.0
        self.check_count = 0

    def start(self):
        """开始监听验证码"""
        if self.is_monitoring:
            logger.debug("[验证码监听] 已在运行中")
            return

        self.is_monitoring = True
        self.start_time = time.time()
        self.check_count = 0
        logger.info(f"[验证码监听] 已启动，将在 {self.auto_stop_seconds} 秒后自动停止")

    def stop(self):
        """停止监听验证码"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        logger.info(f"[验证码监听] 已停止（共检查 {self.check_count} 次）")

    def check_once(self) -> bool:
        """
        执行一次检查（由主线程调用）

        :return: True表示应该继续监听，False表示应该停止
        """
        if not self.is_monitoring:
            return False

        # 检查是否超时
        elapsed = time.time() - self.start_time
        if elapsed > self.auto_stop_seconds:
            logger.info(f"[验证码监听] 已运行 {elapsed:.1f} 秒，自动停止")
            if self.callback:
                self.callback(f"[监听] 已运行 {elapsed:.1f} 秒，自动停止监听")
            self.stop()
            return False

        # 检测验证码
        self.check_count += 1
        try:
            from douyin.search import DouyinSearchManager

            mgr = DouyinSearchManager(self.page)

            if mgr.check_captcha():
                logger.warning("[验证码监听] 检测到验证码！")
                if self.callback:
                    self.callback("[验证码] ⚠️ 检测到验证码，请在浏览器中完成验证")

                # 等待用户完成
                if mgr.wait_for_captcha_completion(timeout=60, callback=self.callback):
                    logger.info("[验证码监听] 验证码已完成")
                    if self.callback:
                        self.callback("[验证码] ✓ 验证完成，可以继续操作")
                else:
                    logger.error("[验证码监听] 验证码超时")
                    if self.callback:
                        self.callback("[验证码] ✗ 验证超时，请重试操作")

                # 验证码处理完成后停止监听
                self.stop()
                return False
        except Exception as e:
            logger.error(f"[验证码监听] 检查异常: {e}")

        return True  # 继续监听
        self.monitor_thread: Optional[threading.Thread] = None
        self.start_time: float = 0.0

    def start(self):
        """开始监听验证码"""
        if self.is_monitoring:
            logger.debug("[验证码监听] 已在运行中")
            return

        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"[验证码监听] 已启动，将在 {self.auto_stop_seconds} 秒后自动停止")

    def stop(self):
        """停止监听验证码"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
        logger.info("[验证码监听] 已停止")

    def _monitor_loop(self):
        """监听循环"""
        from douyin.search import DouyinSearchManager

        try:
            mgr = DouyinSearchManager(self.page)
            check_count = 0

            while self.is_monitoring:
                try:
                    # 检查是否超时
                    elapsed = time.time() - self.start_time
                    if elapsed > self.auto_stop_seconds:
                        logger.info(f"[验证码监听] 已运行 {elapsed:.1f} 秒，自动停止")
                        if self.callback:
                            self.callback(
                                f"[监听] 已运行 {elapsed:.1f} 秒，自动停止监听"
                            )
                        self.stop()
                        break

                    # 检测验证码
                    check_count += 1
                    if mgr.check_captcha():
                        logger.warning("[验证码监听] 检测到验证码！")
                        if self.callback:
                            self.callback(
                                "[验证码] ⚠️ 检测到验证码，请在浏览器中完成验证"
                            )

                        # 等待用户完成
                        if mgr.wait_for_captcha_completion(
                            timeout=60, callback=self.callback
                        ):
                            logger.info("[验证码监听] 验证码已完成")
                            if self.callback:
                                self.callback("[验证码] ✓ 验证完成，可以继续操作")
                        else:
                            logger.error("[验证码监听] 验证码超时")
                            if self.callback:
                                self.callback("[验证码] ✗ 验证超时，请重试操作")

                        # 验证码处理完成后停止监听
                        self.stop()
                        break

                    # 每秒检查一次
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"[验证码监听] 检查异常: {e}")
                    time.sleep(1)

        except Exception as e:
            logger.error(f"[验证码监听] 循环异常: {e}")
        finally:
            self.is_monitoring = False
