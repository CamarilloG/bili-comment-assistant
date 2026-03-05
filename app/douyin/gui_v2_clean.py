# 抖音自动化 GUI v2.0 - 单步操作模式
# 重构版本：每次操作仅执行单步，优化性能，添加Excel式数据展示

from __future__ import annotations

import sys
import os
from pathlib import Path
import time
import traceback
from typing import Optional

# 添加项目路径
current_dir = Path(__file__).parent
app_dir = current_dir.parent
project_root = app_dir.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import ttk, messagebox
import queue

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# 导入组件
from douyin.gui_table import VideoTableFrame
from douyin.captcha_monitor import CaptchaMonitor

# 日志记录器
try:
    from douyin.logger import get_douyin_logger
    logger = get_douyin_logger()
except ImportError:
    try:
        from utils.logger import get_logger
        logger = get_logger()
    except ImportError:
        import logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger(__name__)


# Main GUI class will be added...
