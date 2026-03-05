# 抖音自动化 GUI v2.0 - 单步操作模式
# 重构版本：每次操作仅执行单步，优化性能，添加Excel式数据展示

from __future__ import annotations
import sys, os, time, traceback, queue
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import ttk, messagebox
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# 添加项目路径
current_dir = Path(__file__).parent
app_dir = current_dir.parent
project_root = app_dir.parent
for p in [str(app_dir), str(project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from douyin.gui_table import VideoTableFrame
from douyin.captcha_monitor import CaptchaMonitor

try:
    from douyin.logger import get_douyin_logger
    logger = get_douyin_logger()
except:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

class DouyinGUIv2:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("抖音自动化工具 v2.0 - 单步操作模式")
        self.window.geometry("1200x800")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.is_logged_in = False
        self.captcha_monitor = None
        self.task_queue = queue.Queue()
        self.current_keyword = ""
        self._setup_ui()
        self._start_task_processor()
