# 抖音GUI专用日志记录器
# 记录所有操作、错误、Cookie变化等详细信息

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from loguru import logger as base_logger

    HAS_LOGURU = True
except ImportError:
    import logging

    HAS_LOGURU = False


class DouyinLogger:
    """抖音GUI专用日志记录器"""

    def __init__(self):
        self.log_dir = self._get_log_dir()
        self.log_file = os.path.join(
            self.log_dir, f"douyin_gui_{datetime.now().strftime('%Y%m%d')}.log"
        )
        self._setup_logger()

    def _get_log_dir(self) -> str:
        """获取日志目录"""
        try:
            from core.slot import get_user_data_dir

            log_dir = os.path.join(get_user_data_dir(), "logs", "douyin")
        except:
            # 如果无法获取用户数据目录，使用当前目录
            log_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "logs", "douyin"
            )

        os.makedirs(log_dir, exist_ok=True)
        return log_dir

    def _setup_logger(self):
        """设置日志记录器"""
        if HAS_LOGURU:
            # 使用loguru
            base_logger.add(
                self.log_file,
                rotation="10 MB",
                retention="30 days",
                encoding="utf-8",
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
                level="DEBUG",
                backtrace=True,
                diagnose=True,
            )
            self.logger = base_logger
        else:
            # 使用标准logging
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s",
                handlers=[
                    logging.FileHandler(self.log_file, encoding="utf-8"),
                    logging.StreamHandler(sys.stdout),
                ],
            )
            self.logger = logging.getLogger("douyin_gui")

    def info(self, message: str, **kwargs):
        """记录信息"""
        if HAS_LOGURU:
            self.logger.info(message, **kwargs)
        else:
            self.logger.info(message)

    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        if HAS_LOGURU:
            self.logger.debug(message, **kwargs)
        else:
            self.logger.debug(message)

    def warning(self, message: str, **kwargs):
        """记录警告"""
        if HAS_LOGURU:
            self.logger.warning(message, **kwargs)
        else:
            self.logger.warning(message)

    def error(self, message: str, exc_info: bool = True, **kwargs):
        """记录错误"""
        if HAS_LOGURU:
            self.logger.error(message, **kwargs)
            if exc_info:
                self.logger.exception(message)
        else:
            self.logger.error(message, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = True, **kwargs):
        """记录严重错误"""
        if HAS_LOGURU:
            self.logger.critical(message, **kwargs)
            if exc_info:
                self.logger.exception(message)
        else:
            self.logger.critical(message, exc_info=exc_info)

    def log_operation(self, operation: str, status: str, details: Optional[str] = None):
        """记录操作"""
        msg = f"[操作] {operation} - {status}"
        if details:
            msg += f" | {details}"
        self.info(msg)

    def log_cookie_change(self, action: str, count: int, details: Optional[str] = None):
        """记录Cookie变化"""
        msg = f"[Cookie] {action} - 数量: {count}"
        if details:
            msg += f" | {details}"
        self.info(msg)

    def log_browser_action(
        self, action: str, url: Optional[str] = None, details: Optional[str] = None
    ):
        """记录浏览器操作"""
        msg = f"[浏览器] {action}"
        if url:
            msg += f" | URL: {url}"
        if details:
            msg += f" | {details}"
        self.info(msg)

    def log_search(self, keyword: str, count: int, result_count: int, duration: float):
        """记录搜索操作"""
        msg = f"[搜索] 关键词: {keyword} | 请求数量: {count} | 结果数量: {result_count} | 耗时: {duration:.2f}秒"
        self.info(msg)

    def log_exception(self, operation: str, exception: Exception):
        """记录异常"""
        msg = f"[异常] {operation} 失败"
        self.error(msg, exc_info=True)

        # 记录详细的异常信息
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        exc_trace = traceback.format_exc()

        self.error(f"异常类型: {exc_type}")
        self.error(f"异常信息: {exc_msg}")
        self.error(f"异常堆栈:\n{exc_trace}")

    def get_log_file_path(self) -> str:
        """获取日志文件路径"""
        return self.log_file


# 全局日志记录器实例
_douyin_logger: Optional[DouyinLogger] = None


def get_douyin_logger() -> DouyinLogger:
    """获取抖音日志记录器"""
    global _douyin_logger
    if _douyin_logger is None:
        _douyin_logger = DouyinLogger()
    return _douyin_logger
