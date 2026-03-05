# 抖音自动化 GUI：登录状态检测、登录、搜索
# 使用 tkinter 提供简单的图形界面
# 注意：Playwright 必须在主线程中运行

from __future__ import annotations

import sys
import os
from pathlib import Path
import time
import traceback

# 添加项目路径
current_dir = Path(__file__).parent
app_dir = current_dir.parent
project_root = app_dir.parent
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from typing import Optional
import queue

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# 导入新组件
from douyin.gui_table import VideoTableFrame
from douyin.captcha_monitor import CaptchaMonitor

# 使用专用日志记录器
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


class DouyinGUI:
    """抖音自动化 GUI：检测登录、打开登录页、搜索视频"""

    def __init__(
        self, debug_port: Optional[int] = None, use_local_chrome: bool = False
    ):
        """
        初始化GUI

        :param debug_port: Chrome远程调试端口（可选）
                          如果指定，将启动带调试端口的Chrome
                          可配合MCP工具进行联调
        :param use_local_chrome: 是否使用本地Chrome浏览器（默认False）
                                如果为True，将连接到本地Chrome而不是启动新实例
        """
        self.window = tk.Tk()
        self.window.title("抖音自动化工具 v2.5 - 集成版")
        self.window.geometry("1200x800")  # 增加宽度以容纳表格

        # Playwright 相关
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False

        # 调试配置
        self.debug_port = debug_port
        self.use_local_chrome = use_local_chrome

        # 任务队列
        self.task_queue = queue.Queue()

        # 验证码监听器
        self.captcha_monitor: Optional[CaptchaMonitor] = None

        # Cookie自动保存定时器（将被移除，改为操作后保存）
        self.auto_save_timer = None

        self._setup_ui()
        self._start_task_processor()
        self._auto_load_cookies_on_start()

    def _setup_ui(self):
        """构建界面 - 左右布局：左侧控制面板，右侧表格"""
        # 主容器
        main_container = ttk.Frame(self.window, padding="10")
        main_container.pack(fill="both", expand=True)

        # 左侧控制面板
        left_panel = ttk.Frame(main_container, width=400)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)

        # 右侧数据展示区
        right_panel = ttk.Frame(main_container)
        right_panel.pack(side="right", fill="both", expand=True)

        self._setup_left_panel(left_panel)
        self._setup_right_panel(right_panel)

    def _setup_left_panel(self, parent):
        """构建左侧控制面板"""
        # 标题
        title_label = tk.Label(
            parent, text="抖音自动化工具 v2.5", font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 15))

        # 登录状态区域
        status_frame = tk.LabelFrame(parent, text="登录状态", padx=10, pady=10)
        status_frame.pack(fill="x", pady=5)

        self.status_label = tk.Label(
            status_frame, text="未检测", font=("Arial", 12), fg="gray"
        )
        self.status_label.pack(side="left", padx=5)

        self.check_login_btn = tk.Button(
            status_frame, text="检测登录状态", command=self._on_check_login
        )
        self.check_login_btn.pack(side="left", padx=5)

        self.open_login_btn = tk.Button(
            status_frame,
            text="打开抖音登录",
            command=self._on_open_login,
            state="disabled",
        )
        self.open_login_btn.pack(side="left", padx=5)

        self.save_cookie_btn = tk.Button(
            status_frame, text="手动保存Cookie", command=self._on_save_cookie
        )
        self.save_cookie_btn.pack(side="left", padx=5)

        # 2. 一键搜索区域
        search_frame = tk.LabelFrame(parent, text="2. 一键搜索", padx=10, pady=10)
        search_frame.pack(fill="x", pady=5)

        tk.Label(search_frame, text="关键词:").pack(anchor="w", pady=2)
        self.keyword_entry = tk.Entry(search_frame, width=30)
        self.keyword_entry.pack(fill="x", pady=2)

        self.search_btn = tk.Button(
            search_frame,
            text="一键搜索",
            command=self._on_step_search,
            state="disabled",
        )
        self.search_btn.pack(fill="x", pady=2)

        # 3. 切换筛选区域
        filter_frame = tk.LabelFrame(parent, text="3. 切换筛选", padx=10, pady=10)
        filter_frame.pack(fill="x", pady=5)

        self.filter_btn = tk.Button(
            filter_frame,
            text="切换筛选（最多点赞 + 近七天）",
            command=self._on_step_filter,
            state="disabled",
        )
        self.filter_btn.pack(fill="x", pady=2)

        # 4. 提取视频信息区域
        extract_frame = tk.LabelFrame(parent, text="4. 提取视频信息", padx=10, pady=10)
        extract_frame.pack(fill="x", pady=5)

        count_frame = tk.Frame(extract_frame)
        count_frame.pack(fill="x", pady=2)

        tk.Label(count_frame, text="提取数量:").pack(side="left")
        self.count_spinbox = tk.Spinbox(count_frame, from_=1, to=100, width=8)
        self.count_spinbox.delete(0, "end")
        self.count_spinbox.insert(0, "20")
        self.count_spinbox.pack(side="left", padx=5)

        self.extract_btn = tk.Button(
            extract_frame,
            text="提取视频信息",
            command=self._on_step_extract,
            state="disabled",
        )
        self.extract_btn.pack(fill="x", pady=2)

        # 5. 提取评论区域
        comment_frame = tk.LabelFrame(parent, text="5. 提取评论", padx=10, pady=10)
        comment_frame.pack(fill="x", pady=5)

        tk.Label(comment_frame, text="选择表格中的视频后点击提取").pack(
            anchor="w", pady=2
        )

        comment_count_frame = tk.Frame(comment_frame)
        comment_count_frame.pack(fill="x", pady=2)

        tk.Label(comment_count_frame, text="评论数:").pack(side="left")
        self.comment_count_spinbox = tk.Spinbox(
            comment_count_frame, from_=1, to=50, width=8
        )
        self.comment_count_spinbox.delete(0, "end")
        self.comment_count_spinbox.insert(0, "10")
        self.comment_count_spinbox.pack(side="left", padx=5)

        self.extract_comment_btn = tk.Button(
            comment_frame,
            text="提取选中视频的评论",
            command=self._on_step_extract_comments,
            state="disabled",
        )
        self.extract_comment_btn.pack(fill="x", pady=2)

        # 状态日志区域
        log_frame = tk.LabelFrame(parent, text="操作日志", padx=10, pady=10)
        log_frame.pack(fill="both", expand=True, pady=5)

        self.result_text = scrolledtext.ScrolledText(
            log_frame, wrap=tk.WORD, width=45, height=15, font=("Consolas", 9)
        )
        self.result_text.pack(fill="both", expand=True)

        # 底部按钮
        bottom_frame = tk.Frame(parent)
        bottom_frame.pack(fill="x", pady=10)

        self.clear_btn = tk.Button(
            bottom_frame, text="清空结果", command=self._on_clear_results
        )
        self.clear_btn.pack(side="left", padx=5)

        self.quit_btn = tk.Button(bottom_frame, text="退出", command=self._on_quit)
        self.quit_btn.pack(side="right", padx=5)

    def _setup_right_panel(self, parent):
        """构建右侧数据展示区 - 集成VideoTableFrame"""
        # 标题栏
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=(0, 10))

        tk.Label(title_frame, text="视频数据表格", font=("Arial", 12, "bold")).pack(
            side="left"
        )

        self.video_count_label = tk.Label(
            title_frame, text="共 0 条", font=("Arial", 10), fg="gray"
        )
        self.video_count_label.pack(side="right")

        # 集成VideoTableFrame
        self.video_table = VideoTableFrame(parent)
        self.video_table.pack(fill="both", expand=True)

    def _start_task_processor(self):
        """启动任务处理器（在主线程中处理队列任务）"""

        def process_tasks():
            try:
                # 每次只处理一个任务，避免阻塞太久
                if not self.task_queue.empty():
                    task = self.task_queue.get_nowait()
                    try:
                        task()
                    except Exception as e:
                        logger.error(f"[GUI] 任务执行失败: {e}")
                        import traceback

                        logger.error(f"[GUI] 错误堆栈:\n{traceback.format_exc()}")
            except queue.Empty:
                pass
            finally:
                # 每100ms检查一次队列
                self.window.after(100, process_tasks)

        self.window.after(100, process_tasks)

    def _init_browser(self):
        """初始化浏览器（如果尚未初始化）"""
        if self.playwright is None:
            try:
                logger.info("[GUI] 开始初始化浏览器")
                self.playwright = sync_playwright().start()
                logger.debug("[GUI] Playwright已启动")

                if self.use_local_chrome:
                    # 使用本地Chrome浏览器
                    logger.info("[GUI] 尝试连接到本地Chrome浏览器")
                    logger.info("[GUI] 请确保Chrome已启动并带有调试端口")
                    logger.info(
                        "[GUI] 启动命令: chrome.exe --remote-debugging-port=9222"
                    )

                    # 尝试多个URL（IPv4和IPv6）
                    cdp_urls = [
                        "http://127.0.0.1:9222",  # IPv4优先
                        "http://localhost:9222",
                    ]

                    connected = False
                    for cdp_url in cdp_urls:
                        try:
                            logger.info(f"[GUI] 尝试连接: {cdp_url}")
                            # 尝试连接到本地Chrome
                            self.browser = self.playwright.chromium.connect_over_cdp(
                                cdp_url
                            )
                            logger.info(f"[GUI] 成功连接到本地Chrome: {cdp_url}")
                            connected = True
                            break
                        except Exception as e:
                            logger.debug(f"[GUI] 连接 {cdp_url} 失败: {e}")
                            continue

                    if not connected:
                        logger.error("[GUI] 所有连接尝试都失败")
                        logger.error("[GUI] 请确保Chrome已启动:")
                        logger.error("[GUI]   chrome.exe --remote-debugging-port=9222")
                        logger.info("[GUI] 将启动新的浏览器实例")
                        # 继续使用新实例
                    else:
                        # 获取现有的上下文和页面
                        contexts = self.browser.contexts
                        if len(contexts) > 0:
                            self.context = contexts[0]
                            logger.info(f"[GUI] 使用现有浏览器上下文")

                            pages = self.context.pages
                            if len(pages) > 0:
                                self.page = pages[0]
                                logger.info(f"[GUI] 使用现有页面: {self.page.url}")
                            else:
                                self.page = self.context.new_page()
                                logger.info("[GUI] 创建新页面")
                        else:
                            # 如果没有上下文，创建新的
                            self.context = self.browser.new_context()
                            self.page = self.context.new_page()
                            logger.info("[GUI] 创建新的浏览器上下文和页面")

                        logger.info("[GUI] 本地Chrome浏览器连接完成")
                        # 不需要注入Cookie，因为使用的是本地浏览器
                        return

                # 启动新的浏览器实例
                # 配置浏览器启动参数
                launch_kwargs = {"headless": False}

                # 如果指定了调试端口，添加远程调试参数
                if self.debug_port:
                    launch_kwargs["args"] = [
                        f"--remote-debugging-port={self.debug_port}",
                        "--no-first-run",
                        "--no-default-browser-check",
                    ]
                    logger.info(f"[GUI] 启用Chrome远程调试端口: {self.debug_port}")
                    logger.info(
                        f"[GUI] 可通过 chrome://inspect 或 http://localhost:{self.debug_port} 连接"
                    )

                self.browser = self.playwright.chromium.launch(**launch_kwargs)
                logger.debug("[GUI] Chromium浏览器已启动")

                self.context = self.browser.new_context()
                logger.debug("[GUI] 浏览器上下文已创建")

                self.page = self.context.new_page()
                logger.debug("[GUI] 新页面已创建")

                logger.info("[GUI] 浏览器初始化完成")

                # 自动加载本地Cookie
                self._auto_inject_cookies()

                # 启动定期保存Cookie
                self._start_auto_save_cookies()

            except Exception as e:
                logger.error(f"[GUI] 浏览器初始化失败: {e}")
                logger.error(f"[GUI] 错误堆栈:\n{traceback.format_exc()}")
                raise

    def _auto_load_cookies_on_start(self):
        """启动时检查是否有保存的Cookie"""
        from douyin.auth import load_douyin_cookies, get_douyin_cookie_path

        cookies = load_douyin_cookies()
        cookie_path = get_douyin_cookie_path()

        if cookies:
            self._log_result(f"[INFO] 发现本地Cookie文件: {cookie_path}")
            self._log_result(f"[INFO] 已加载 {len(cookies)} 个Cookie，启动时将自动使用")
            self._log_result("[提示] 点击「检测登录状态」验证Cookie是否有效")
        else:
            self._log_result("[INFO] 未找到本地Cookie，首次使用需要登录")
            self._log_result("[提示] 点击「打开抖音登录」进行登录")

    def _auto_inject_cookies(self):
        """自动注入本地Cookie到浏览器"""
        if self.page is None:
            return

        from douyin.auth import inject_douyin_cookies_to_page, load_douyin_cookies

        cookies = load_douyin_cookies()
        if cookies:
            try:
                inject_douyin_cookies_to_page(self.page)
                logger.info(f"[GUI] 已自动注入 {len(cookies)} 个Cookie")
            except Exception as e:
                logger.warning(f"[GUI] 自动注入Cookie失败: {e}")

    def _start_auto_save_cookies(self):
        """启动定期自动保存Cookie（每60秒，减少频率避免卡顿）"""

        def auto_save():
            try:
                if self.context is not None:
                    self._save_current_cookies(silent=True)
            except Exception as e:
                logger.debug(f"[GUI] 自动保存Cookie失败: {e}")
            finally:
                # 60秒后再次执行（从30秒改为60秒）
                self.auto_save_timer = self.window.after(60000, auto_save)

        # 首次延迟10秒执行（从5秒改为10秒）
        self.auto_save_timer = self.window.after(10000, auto_save)

    def _save_current_cookies(self, silent=False):
        """保存当前浏览器的Cookie"""
        if self.context is None:
            return False

        try:
            from douyin.auth import save_douyin_cookies
            from datetime import datetime

            cookies = self.context.cookies()
            if not cookies:
                return False

            # 只保存抖音相关的Cookie
            douyin_cookies = [
                dict(c) for c in cookies if "douyin.com" in c.get("domain", "")
            ]

            if not douyin_cookies:
                return False

            save_douyin_cookies(
                douyin_cookies,
                meta={
                    "updated_at": datetime.now().isoformat(),
                    "source": "gui_auto_save",
                },
            )

            if not silent:
                self._log_result(f"[OK] 已保存 {len(douyin_cookies)} 个Cookie")

            logger.info(f"[GUI] Cookie已保存: {len(douyin_cookies)} 个")
            return True

        except Exception as e:
            logger.error(f"[GUI] 保存Cookie失败: {e}")
            if not silent:
                self._log_result(f"[FAIL] 保存Cookie失败: {e}")
            return False

    def _update_status(self, is_logged_in: bool):
        """更新登录状态显示"""
        self.is_logged_in = is_logged_in
        if is_logged_in:
            self.status_label.config(text="已登录", fg="green")
            self.open_login_btn.config(state="disabled")
            self.search_btn.config(state="normal")
        else:
            self.status_label.config(text="未登录", fg="red")
            self.open_login_btn.config(state="normal")
            self.search_btn.config(state="disabled")

    def _log_result(self, message: str):
        """在结果区域显示消息"""
        self.result_text.insert(tk.END, message + "\n")
        self.result_text.see(tk.END)
        # 减少 update_idletasks 调用频率，避免卡顿
        # 只在必要时更新（例如验证码提示）
        # self.window.update_idletasks()

    def _on_check_login(self):
        """检测登录状态"""

        def task():
            try:
                logger.info("[GUI] 开始检测登录状态")
                self._log_result("=" * 50)
                self._log_result("正在检测登录状态...")
                self._init_browser()

                if self.page is None:
                    error_msg = "浏览器初始化失败"
                    logger.error(f"[GUI] {error_msg}")
                    self._log_result(f"[FAIL] {error_msg}")
                    return

                # 注入本地 Cookie
                from douyin.auth import (
                    inject_douyin_cookies_to_page,
                    load_douyin_cookies,
                )

                cookies = load_douyin_cookies()
                if cookies:
                    self._log_result(f"[INFO] 加载了 {len(cookies)} 个本地 Cookie")
                    logger.info(f"[GUI] 加载了 {len(cookies)} 个本地Cookie")
                else:
                    self._log_result("[INFO] 未找到本地 Cookie")
                    logger.info("[GUI] 未找到本地Cookie")

                inject_douyin_cookies_to_page(self.page)
                logger.debug("[GUI] Cookie已注入到页面")

                # 打开首页并检查登录状态
                from douyin.search import DouyinSearchManager

                mgr = DouyinSearchManager(self.page)

                self._log_result("[INFO] 正在打开抖音首页...")
                logger.info("[GUI] 正在打开抖音首页")

                if not mgr.open_homepage():
                    logger.error("[GUI] 打开首页失败")
                    self._log_result("[FAIL] 打开首页失败")
                    return

                self._log_result("[INFO] 正在检查登录状态...")
                logger.info("[GUI] 正在检查登录状态")

                is_logged_in = mgr.check_login_status()
                logger.info(f"[GUI] 登录状态检测结果: {is_logged_in}")

                self._update_status(is_logged_in)

                if is_logged_in:
                    self._log_result("[OK] ✓ 检测完成：已登录")
                    self._log_result("可以开始搜索视频了！")
                    logger.info("[GUI] 登录状态检测成功：已登录")
                else:
                    self._log_result("[FAIL] ✗ 检测完成：未登录")
                    self._log_result("请点击「打开抖音登录」按钮进行登录")
                    logger.info("[GUI] 登录状态检测成功：未登录")

                self._log_result("=" * 50)

            except Exception as e:
                error_msg = str(e)
                error_trace = traceback.format_exc()

                logger.error(f"[GUI] 检测登录状态失败: {error_msg}")
                logger.error(f"[GUI] 错误堆栈:\n{error_trace}")

                self._log_result(f"[FAIL] 检测失败: {error_msg}")
                self._log_result("详细错误信息已记录到日志文件")

        self.task_queue.put(task)

    def _on_open_login(self):
        """打开抖音登录页面供用户登录"""

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result("正在打开抖音登录页面...")
                self._init_browser()

                if self.page is None or self.context is None:
                    self._log_result("[FAIL] 浏览器初始化失败")
                    return

                # 打开首页
                self.page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
                self._log_result("[OK] 已打开抖音首页，请在浏览器中完成登录")
                self._log_result("")
                self._log_result("登录方式：")
                self._log_result("  1. 扫码登录（推荐）")
                self._log_result("  2. 密码登录")
                self._log_result("")
                self._log_result("[提示] 登录成功后，Cookie会自动保存")
                self._log_result("[提示] 下次启动时会自动使用保存的Cookie")
                self._log_result("=" * 50)

                # 多次尝试保存Cookie（登录后可能需要一些时间）
                save_attempts = [5000, 10000, 15000, 20000]  # 5秒、10秒、15秒、20秒

                for delay in save_attempts:

                    def make_save_task(attempt_num):
                        def save_cookies_task():
                            try:
                                if self.context is None:
                                    return

                                cookies = self.context.cookies()
                                # 只保存抖音相关的Cookie
                                douyin_cookies = [
                                    dict(c)
                                    for c in cookies
                                    if "douyin.com" in c.get("domain", "")
                                ]

                                if douyin_cookies:
                                    from douyin.auth import save_douyin_cookies
                                    from datetime import datetime

                                    save_douyin_cookies(
                                        douyin_cookies,
                                        meta={
                                            "updated_at": datetime.now().isoformat(),
                                            "source": "manual_login",
                                        },
                                    )

                                    # 只在第一次成功保存时显示消息
                                    if attempt_num == 1:
                                        self._log_result(
                                            f"[OK] ✓ Cookie已自动保存 ({len(douyin_cookies)}个)"
                                        )
                                        self._log_result("[提示] 下次启动时会自动登录")

                                    logger.info(
                                        f"[GUI] Cookie自动保存成功 (尝试{attempt_num}): {len(douyin_cookies)}个"
                                    )

                            except Exception as e:
                                logger.debug(
                                    f"[GUI] Cookie保存尝试{attempt_num}失败: {e}"
                                )

                        return save_cookies_task

                    self.window.after(
                        delay,
                        lambda t=make_save_task(save_attempts.index(delay) + 1): (
                            self.task_queue.put(t)
                        ),
                    )

            except Exception as e:
                logger.error(f"[GUI] 打开登录页面失败: {e}")
                self._log_result(f"[FAIL] 打开失败: {e}")

        self.task_queue.put(task)

    # ========== 单步操作方法 ==========

    def _on_step_search(self):
        """步骤2: 一键搜索"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result(f"[步骤2] 开始搜索: {keyword}")
                self._log_result("=" * 50)

                if self.page is None:
                    self._log_result("[失败] 浏览器未初始化，请先检测登录状态")
                    return

                from douyin.search import DouyinSearchManager
                import random

                mgr = DouyinSearchManager(self.page)

                # 启动验证码监听
                self._start_captcha_monitor()

                # 定位搜索框
                self._log_result("[信息] 定位搜索框...")
                input_el = mgr._get_search_input_locator()
                input_el.wait_for(state="visible", timeout=10000)

                # 模拟输入
                self._log_result(f"[信息] 输入关键词: {keyword}")
                input_el.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.3, 0.6))
                input_el.click()
                time.sleep(random.uniform(0.2, 0.4))
                input_el.fill("")
                time.sleep(random.uniform(0.1, 0.3))
                input_el.type(keyword, delay=random.randint(80, 150))
                time.sleep(random.uniform(0.3, 0.6))

                # 点击搜索按钮
                self._log_result("[信息] 点击搜索按钮...")
                btn = mgr._get_search_btn_locator()
                if btn.count() == 0 or not btn.is_visible():
                    self._log_result("[失败] 未找到搜索按钮")
                    return

                btn.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.2, 0.4))
                btn.click()

                # 等待页面加载
                wait_time = random.uniform(2.0, 3.0)
                self._log_result(f"[信息] 等待搜索结果加载...")
                time.sleep(wait_time)

                self._log_result(f"[成功] ✓ 搜索完成")
                self._log_result(f"[提示] 当前URL: {self.page.url}")
                self._log_result("[提示] 可以点击「切换筛选」或直接「提取视频信息」")
                self._log_result("=" * 50)

                # 启用后续按钮
                self.filter_btn.config(state="normal")
                self.extract_btn.config(state="normal")

            except Exception as e:
                logger.error(f"[GUI] 搜索失败: {e}")
                self._log_result(f"[错误] 搜索失败: {str(e)}")

        self.task_queue.put(task)

    def _on_step_filter(self):
        """步骤3: 切换筛选"""

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result("[步骤3] 正在切换筛选条件...")
                self._log_result("=" * 50)

                if self.page is None:
                    self._log_result("[失败] 浏览器未初始化")
                    return

                from douyin.search import DouyinSearchManager

                mgr = DouyinSearchManager(self.page)

                # 启动验证码监听
                self._start_captcha_monitor()

                # 切换到视频标签
                self._log_result("[信息] 切换到视频标签...")
                if mgr._switch_to_video_tab():
                    self._log_result("[成功] ✓ 已切换到视频标签")
                else:
                    self._log_result("[警告] 切换视频标签失败，尝试继续")

                # 应用筛选：最多点赞 + 一周内
                self._log_result("[信息] 应用筛选条件（最多点赞 + 近七天）...")
                if mgr._apply_filters(sort_by="most_liked", time_range="week"):
                    self._log_result("[成功] ✓ 筛选条件已应用")
                else:
                    self._log_result("[警告] 应用筛选失败，使用默认排序")

                self._log_result("[提示] 可以点击「提取视频信息」")
                self._log_result("=" * 50)

            except Exception as e:
                logger.error(f"[GUI] 切换筛选失败: {e}")
                self._log_result(f"[错误] 切换筛选失败: {str(e)}")

        self.task_queue.put(task)

    def _on_step_extract(self):
        """步骤4: 提取视频信息"""
        try:
            max_count = int(self.count_spinbox.get())
        except ValueError:
            messagebox.showwarning("提示", "数量必须是数字")
            return

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result(f"[步骤4] 开始提取 {max_count} 个视频...")
                self._log_result("=" * 50)

                if self.page is None:
                    self._log_result("[失败] 浏览器未初始化")
                    return

                from douyin.search import DouyinSearchManager

                mgr = DouyinSearchManager(self.page)

                # 启动验证码监听
                self._start_captcha_monitor()

                # 提取视频信息
                self._log_result("[信息] 正在提取视频信息...")
                videos = mgr.get_current_page_videos(max_count)

                if videos:
                    # 清空表格并添加视频
                    self.video_table.clear()
                    for video in videos:
                        self.video_table.add_video(video)

                    # 更新视频计数
                    self.video_count_label.config(text=f"共 {len(videos)} 条")

                    self._log_result(f"[成功] ✓ 成功提取 {len(videos)} 个视频")
                    self._log_result("[提示] 视频已显示在右侧表格中")
                    self._log_result("[提示] 选择视频后可以点击「提取选中视频的评论」")

                    # 在日志中显示前5个视频
                    for i, video in enumerate(videos[:5], 1):
                        title = video.get("title", "Unknown")
                        self._log_result(f"  {i}. {title[:40]}...")

                    if len(videos) > 5:
                        self._log_result(f"  ... 还有 {len(videos) - 5} 个视频")

                    # 启用评论提取按钮
                    self.extract_comment_btn.config(state="normal")
                else:
                    self._log_result("[失败] 未提取到视频")
                    self._log_result("[提示] 请检查搜索结果或重新搜索")

                self._log_result("=" * 50)

            except Exception as e:
                logger.error(f"[GUI] 提取视频失败: {e}")
                self._log_result(f"[错误] 提取视频失败: {str(e)}")

        self.task_queue.put(task)

    def _on_step_extract_comments(self):
        """步骤5: 提取选中视频的评论"""
        result = self.video_table.get_selected_video()
        if not result:
            messagebox.showwarning("提示", "请先在表格中选择一个视频")
            return

        index, video = result

        try:
            comment_count = int(self.comment_count_spinbox.get())
        except ValueError:
            comment_count = 10

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result(f"[步骤5] 正在提取视频评论...")
                self._log_result(f"视频: {video.get('title', 'Unknown')[:40]}...")
                self._log_result("=" * 50)

                if self.page is None:
                    self._log_result("[失败] 浏览器未初始化")
                    return

                from douyin.search import DouyinSearchManager

                mgr = DouyinSearchManager(self.page)

                # 启动验证码监听
                self._start_captcha_monitor()

                # 更新状态
                self.video_table.update_video_status(index, "处理中...")

                # 提取视频ID
                video_id = video.get("url", "").split("/")[-1]
                if not video_id:
                    self._log_result("[失败] 无法获取视频ID")
                    self.video_table.update_video_status(index, "失败")
                    return

                # 点击视频（带验证码检测）
                self._log_result("[信息] 进入视频详情页...")
                if not mgr.click_video_card(
                    video_id, wait_for_load=True, captcha_callback=self._log_result
                ):
                    self._log_result("[失败] 点击视频失败")
                    self.video_table.update_video_status(index, "点击失败")
                    return

                self._log_result("[成功] ✓ 已进入视频详情页")

                # 点击评论按钮
                self._log_result("[信息] 打开评论区...")
                if not mgr.click_comment_button():
                    self._log_result("[失败] 打开评论区失败")
                    self.video_table.update_video_status(index, "打开评论失败")
                    self.page.go_back()
                    time.sleep(1)
                    return

                self._log_result("[成功] ✓ 评论区已打开")

                # 获取评论
                self._log_result(f"[信息] 获取评论（最多{comment_count}条）...")
                comments = mgr.get_comments(max_count=comment_count)

                if comments:
                    self.video_table.update_video_status(
                        index, "已完成", comment_count=len(comments), comments=comments
                    )
                    self._log_result(f"[成功] ✓ 成功获取 {len(comments)} 条评论")

                    # 显示前3条评论
                    for i, comment in enumerate(comments[:3], 1):
                        username = comment.get("username", "Unknown")
                        content = comment.get("content", "")[:30]
                        self._log_result(f"  评论{i}: {username} - {content}...")

                    if len(comments) > 3:
                        self._log_result(f"  ... 还有 {len(comments) - 3} 条评论")
                else:
                    self.video_table.update_video_status(index, "无评论")
                    self._log_result("[信息] 该视频暂无评论")

                # 返回搜索页
                self._log_result("[信息] 返回搜索页...")
                self.page.go_back()
                time.sleep(1)

                self._log_result("=" * 50)

            except Exception as e:
                logger.error(f"[GUI] 提取评论失败: {e}")
                self.video_table.update_video_status(index, f"失败: {str(e)[:20]}")
                self._log_result(f"[错误] 提取评论失败: {str(e)}")
                # 尝试返回
                try:
                    self.page.go_back()
                    time.sleep(1)
                except:
                    pass

        self.task_queue.put(task)

    def _on_search(self):
        """执行搜索"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return

        try:
            max_count = int(self.count_spinbox.get())
        except ValueError:
            messagebox.showwarning("提示", "数量必须是数字")
            return

        # 获取评论选项
        fetch_comments = self.fetch_comments_var.get()
        try:
            comment_count = int(self.comment_count_spinbox.get())
        except ValueError:
            comment_count = 10

        def task():
            start_time = time.time()
            try:
                logger.info(
                    f"[GUI] 开始搜索: keyword={keyword}, max_count={max_count}, fetch_comments={fetch_comments}"
                )
                self._log_result("=" * 50)
                self._log_result(f"开始搜索: {keyword} (最多 {max_count} 条)")
                if fetch_comments:
                    self._log_result(
                        f"将获取每个视频的评论 (每个视频 {comment_count} 条)"
                    )
                self._log_result("=" * 50)

                if self.page is None:
                    error_msg = "浏览器未初始化，请先检测登录状态"
                    logger.error(f"[GUI] {error_msg}")
                    self._log_result(f"[FAIL] {error_msg}")
                    return

                # 检查登录状态
                if not self.is_logged_in:
                    logger.warning("[GUI] 未登录状态下尝试搜索")
                    self._log_result("[警告] 当前未登录，搜索结果可能不完整")
                    self._log_result("[提示] 建议先点击「检测登录状态」确认登录")

                # 定义验证码回调函数，用于在GUI中显示提示
                def captcha_callback(message: str):
                    """验证码提示回调"""
                    self._log_result(message)
                    # 只在验证码相关消息时强制更新界面
                    if "[验证码]" in message:
                        self.window.update()  # 立即更新界面

                # 执行搜索（不再重复注入Cookie）
                logger.info("[GUI] 调用 run_search_flow")
                from douyin.flow import run_search_flow

                videos = run_search_flow(
                    self.page,
                    keyword=keyword,
                    max_count=max_count,
                    inject_cookie=False,  # 改为False
                    captcha_callback=captcha_callback,  # 传入回调函数
                )

                duration = time.time() - start_time
                logger.info(
                    f"[GUI] 搜索完成: 找到 {len(videos) if videos else 0} 个视频, 耗时 {duration:.2f}秒"
                )

                if not videos:
                    self._log_result("[FAIL] 未找到视频结果")
                    self._log_result("")
                    self._log_result("可能的原因：")
                    self._log_result("  1. 关键词没有相关视频")
                    self._log_result("  2. 网络连接问题")
                    self._log_result("  3. 未登录或登录已过期")
                    self._log_result("  4. 验证码未完成或超时")
                    self._log_result("")
                    self._log_result("建议：")
                    self._log_result("  - 更换关键词重试")
                    self._log_result("  - 检查网络连接")
                    self._log_result("  - 点击「检测登录状态」确认登录")
                    self._log_result("  - 如遇验证码，请及时在浏览器中完成")
                    return

                self._log_result(
                    f"[OK] ✓ 找到 {len(videos)} 个视频 (耗时 {duration:.2f}秒)\n"
                )

                # 清空表格并添加视频
                self.video_table.clear()
                for video in videos:
                    self.video_table.add_video(video)

                # 更新视频计数
                self.video_count_label.config(text=f"共 {len(videos)} 条")

                # 在日志中显示视频列表
                for i, video in enumerate(videos, 1):
                    title = video.get("title", "Unknown")
                    author = video.get("author", "Unknown")
                    url = video.get("url", "")

                    self._log_result(f"{i}. {title}")
                    self._log_result(f"   作者: {author}")
                    self._log_result(f"   链接: {url}")
                    self._log_result("")

                    logger.debug(
                        f"[GUI] 视频 {i}: title={title}, author={author}, url={url}"
                    )

                # 启动验证码监听（10秒）
                self._start_captcha_monitor()

                # 如果需要获取评论
                if fetch_comments and videos:
                    self._log_result("=" * 50)
                    self._log_result("开始获取评论...")
                    self._log_result("=" * 50)

                    from douyin.search import DouyinSearchManager

                    mgr = DouyinSearchManager(self.page)

                    for i, video in enumerate(videos, 1):
                        try:
                            video_id = video.get("url", "").split("/")[-1]
                            if not video_id:
                                continue

                            self._log_result(
                                f"\n[{i}/{len(videos)}] 处理视频: {video.get('title', 'Unknown')[:40]}..."
                            )

                            # 点击视频
                            self._log_result(f"  → 点击视频...")
                            if not mgr.click_video_card(
                                video_id,
                                wait_for_load=True,
                                captcha_callback=captcha_callback,
                            ):
                                self._log_result(f"  ✗ 点击失败，跳过")
                                continue

                            self._log_result(f"  ✓ 已进入视频详情页")

                            # 点击评论按钮
                            self._log_result(f"  → 打开评论区...")
                            if not mgr.click_comment_button():
                                self._log_result(f"  ✗ 打开评论区失败，跳过")
                                # 返回搜索页
                                self.page.go_back()
                                time.sleep(1)
                                continue

                            self._log_result(f"  ✓ 评论区已打开")

                            # 获取评论
                            self._log_result(f"  → 获取评论...")
                            comments = mgr.get_comments(max_count=comment_count)

                            if comments:
                                self._log_result(f"  ✓ 获取到 {len(comments)} 条评论\n")

                                for j, comment in enumerate(
                                    comments[:5], 1
                                ):  # 只显示前5条
                                    self._log_result(f"    评论 {j}:")
                                    self._log_result(
                                        f"      用户: {comment.get('username', 'Unknown')}"
                                    )
                                    self._log_result(
                                        f"      内容: {comment.get('content', 'Unknown')[:50]}..."
                                    )
                                    self._log_result(
                                        f"      点赞: {comment.get('likes', '0')} | 时间: {comment.get('time', 'Unknown')}"
                                    )

                                if len(comments) > 5:
                                    self._log_result(
                                        f"    ... 还有 {len(comments) - 5} 条评论"
                                    )

                                # 保存评论到视频信息中
                                video["comments"] = comments
                            else:
                                self._log_result(f"  ✗ 未获取到评论")

                            # 返回搜索页
                            self._log_result(f"  → 返回搜索页...")
                            self.page.go_back()
                            time.sleep(1)

                        except Exception as e:
                            logger.error(f"[GUI] 处理视频 {i} 评论失败: {e}")
                            self._log_result(f"  ✗ 处理失败: {str(e)}")
                            # 尝试返回搜索页
                            try:
                                self.page.go_back()
                                time.sleep(1)
                            except:
                                pass

                    self._log_result("\n" + "=" * 50)
                    self._log_result("评论获取完成")
                    self._log_result("=" * 50)

                self._log_result("\n" + "=" * 50)
                logger.info(f"[GUI] 搜索结果已显示")

            except Exception as e:
                duration = time.time() - start_time
                error_msg = str(e)
                error_trace = traceback.format_exc()

                logger.error(f"[GUI] 搜索失败: {error_msg}")
                logger.error(f"[GUI] 错误堆栈:\n{error_trace}")

                self._log_result(f"[FAIL] ✗ 搜索失败 (耗时 {duration:.2f}秒)")
                self._log_result(f"错误信息: {error_msg}")
                self._log_result("")
                self._log_result("详细错误信息已记录到日志文件")

                # 尝试获取日志文件路径
                try:
                    if hasattr(logger, "get_log_file_path"):
                        log_path = logger.get_log_file_path()
                    else:
                        log_path = "用户数据/logs/douyin"
                    self._log_result(f"日志位置: {log_path}")
                except:
                    self._log_result("日志位置: 用户数据/logs/douyin")

                self._log_result("")
                self._log_result("请尝试：")
                self._log_result("  1. 重新检测登录状态")
                self._log_result("  2. 重启程序")
                self._log_result("  3. 检查网络连接")
                self._log_result("  4. 如遇验证码，请及时完成")
                self._log_result("=" * 50)

        self.task_queue.put(task)

    def _on_clear_results(self):
        """清空结果显示"""
        self.result_text.delete(1.0, tk.END)

    def _on_save_cookie(self):
        """手动保存Cookie"""

        def task():
            try:
                self._log_result("=" * 50)
                self._log_result("正在手动保存Cookie...")

                if self.context is None:
                    self._log_result("[FAIL] 浏览器未初始化")
                    return

                success = self._save_current_cookies(silent=False)

                if success:
                    self._log_result("[提示] Cookie已保存，下次启动时会自动使用")
                else:
                    self._log_result("[FAIL] 未找到有效的Cookie")

                self._log_result("=" * 50)

            except Exception as e:
                logger.error(f"[GUI] 手动保存Cookie失败: {e}")
                self._log_result(f"[FAIL] 保存失败: {e}")

        self.task_queue.put(task)

    def _start_captcha_monitor(self):
        """启动验证码监听（10秒后自动停止）"""
        # 注意：由于Playwright的线程限制，暂时禁用后台监听
        # 验证码检测已集成到各个操作中，会在需要时自动检测
        if self.page:
            # 停止之前的监听器
            if self.captcha_monitor:
                self.captcha_monitor.stop()
            
            # 记录日志但不启动后台监听
            self._log_result("[提示] 验证码检测已启用（操作中自动检测）")
            logger.info("[GUI] 验证码检测已启用")

    def _on_quit(self):
        """退出程序"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self._cleanup()
            self.window.quit()

    def _cleanup(self):
        """清理资源"""
        try:
            logger.info("[GUI] 开始清理资源")

            # 停止验证码监听器
            if self.captcha_monitor:
                logger.debug("[GUI] 停止验证码监听器")
                self.captcha_monitor.stop()
                self.captcha_monitor = None

            # 停止自动保存定时器
            if self.auto_save_timer:
                logger.debug("[GUI] 取消自动保存定时器")
                self.window.after_cancel(self.auto_save_timer)
                self.auto_save_timer = None

            # 最后一次保存Cookie
            if self.context:
                logger.info("[GUI] 执行最后一次Cookie保存")
                self._save_current_cookies(silent=True)

            # 关闭浏览器
            if self.page:
                logger.debug("[GUI] 关闭页面")
                self.page.close()
            if self.context:
                logger.debug("[GUI] 关闭浏览器上下文")
                self.context.close()
            if self.browser:
                logger.debug("[GUI] 关闭浏览器")
                self.browser.close()
            if self.playwright:
                logger.debug("[GUI] 停止Playwright")
                self.playwright.stop()

            logger.info("[GUI] 资源清理完成")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.warning(f"[GUI] 清理资源时出错: {e}")
            logger.warning(f"[GUI] 错误堆栈:\n{error_trace}")

    def run(self):
        """启动 GUI"""
        try:
            logger.info("[GUI] 启动抖音自动化GUI")
            logger.info(f"[GUI] Python版本: {sys.version}")
            logger.info(f"[GUI] 工作目录: {os.getcwd()}")

            self.window.protocol("WM_DELETE_WINDOW", self._on_quit)
            self.window.mainloop()

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.critical(f"[GUI] GUI运行失败: {e}")
            logger.critical(f"[GUI] 错误堆栈:\n{error_trace}")
            raise


def main():
    """启动抖音 GUI"""
    import argparse

    try:
        # 解析命令行参数
        parser = argparse.ArgumentParser(description="抖音自动化GUI")
        parser.add_argument(
            "--debug-port",
            type=int,
            default=None,
            help="Chrome远程调试端口（例如：9222），用于MCP工具联调",
        )
        parser.add_argument(
            "--use-local-chrome",
            action="store_true",
            help="使用本地Chrome浏览器（需要先启动Chrome并带调试端口）",
        )

        args = parser.parse_args()

        logger.info("=" * 60)
        logger.info("抖音自动化GUI启动")
        if args.debug_port:
            logger.info(f"调试模式：端口 {args.debug_port}")
        if args.use_local_chrome:
            logger.info("使用本地Chrome浏览器")
            logger.info("请确保Chrome已启动: chrome.exe --remote-debugging-port=9222")
        logger.info("=" * 60)

        app = DouyinGUI(
            debug_port=args.debug_port, use_local_chrome=args.use_local_chrome
        )
        app.run()

        logger.info("=" * 60)
        logger.info("抖音自动化GUI已退出")
        logger.info("=" * 60)

    except Exception as e:
        error_trace = traceback.format_exc()
        logger.critical(f"程序启动失败: {e}")
        logger.critical(f"错误堆栈:\n{error_trace}")

        # 显示错误对话框
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "启动失败", f"程序启动失败:\n\n{e}\n\n详细信息请查看日志文件"
            )
        except:
            pass

        raise


if __name__ == "__main__":
    main()
