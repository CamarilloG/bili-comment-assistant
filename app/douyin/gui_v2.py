# 抖音自动化 GUI v2.0 - 单步操作模式
# 重构版本：每次操作仅执行单步，优化性能，添加Excel式数据展示

from __future__ import annotations

import sys
import os
from pathlib import Path
import time
import traceback
import threading
from typing import Optional, List, Dict

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


class CaptchaMonitor:
    """验证码监听器 - 智能监听，定时自动停止"""

    def __init__(self, page: Page, callback=None, auto_stop_seconds: int = 10):
        self.page = page
        self.callback = callback
        self.auto_stop_seconds = auto_stop_seconds
        self.is_monitoring = False
        self.monitor_thread = None
        self.start_time = None

    def start(self):
        """开始监听验证码"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.start_time = time.time()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info(f"[验证码监听] 已启动，将在 {self.auto_stop_seconds} 秒后自动停止")

    def stop(self):
        """停止监听验证码"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.info("[验证码监听] 已停止")

    def _monitor_loop(self):
        """监听循环"""
        from douyin.search import DouyinSearchManager

        mgr = DouyinSearchManager(self.page)
        check_count = 0

        while self.is_monitoring:
            try:
                # 检查是否超时
                elapsed = time.time() - self.start_time
                if elapsed > self.auto_stop_seconds:
                    logger.info(f"[验证码监听] 已运行 {elapsed:.1f} 秒，自动停止")
                    self.stop()
                    break

                # 检测验证码
                check_count += 1
                if mgr.check_captcha():
                    logger.warning("[验证码监听] 检测到验证码！")
                    if self.callback:
                        self.callback("[验证码] 检测到验证码，请在浏览器中完成验证")

                    # 等待用户完成
                    if mgr.wait_for_captcha_completion(
                        timeout=60, callback=self.callback
                    ):
                        logger.info("[验证码监听] 验证码已完成")
                        if self.callback:
                            self.callback("[验证码] 验证完成，可以继续操作")
                    else:
                        logger.error("[验证码监听] 验证码超时")
                        if self.callback:
                            self.callback("[验证码] 验证超时，请重试操作")

                    # 验证码处理完成后停止监听
                    self.stop()
                    break

                # 每秒检查一次
                time.sleep(1)

            except Exception as e:
                logger.error(f"[验证码监听] 异常: {e}")
                break


class VideoTableFrame(ttk.Frame):
    """Excel式视频信息表格组件"""

    def __init__(self, parent):
        super().__init__(parent)
        self.videos: List[Dict] = []
        self._setup_ui()

    def _setup_ui(self):
        """构建表格UI"""
        # 创建Treeview表格
        columns = ("序号", "标题", "作者", "链接", "点赞数", "评论数", "状态")

        self.tree = ttk.Treeview(
            self, columns=columns, show="headings", selectmode="browse", height=15
        )

        # 设置列标题和宽度
        column_widths = {
            "序号": 50,
            "标题": 300,
            "作者": 100,
            "链接": 200,
            "点赞数": 80,
            "评论数": 80,
            "状态": 100,
        }

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=column_widths.get(col, 100), anchor="w")

        # 添加滚动条
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        # 布局
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def add_video(self, video: Dict):
        """添加视频到表格"""
        self.videos.append(video)
        idx = len(self.videos)

        values = (
            idx,
            video.get("title", "Unknown")[:50],
            video.get("author", "Unknown"),
            video.get("url", "")[:40] + "...",
            video.get("likes", "-"),
            video.get("comment_count", "-"),
            video.get("status", "待处理"),
        )

        self.tree.insert("", "end", values=values, tags=(str(idx),))

    def update_video_status(self, index: int, status: str, **kwargs):
        """更新视频状态"""
        if 0 <= index < len(self.videos):
            self.videos[index]["status"] = status
            for key, value in kwargs.items():
                self.videos[index][key] = value

            # 更新表格显示
            item_id = self.tree.get_children()[index]
            video = self.videos[index]
            values = (
                index + 1,
                video.get("title", "Unknown")[:50],
                video.get("author", "Unknown"),
                video.get("url", "")[:40] + "...",
                video.get("likes", "-"),
                video.get("comment_count", "-"),
                status,
            )
            self.tree.item(item_id, values=values)

    def clear(self):
        """清空表格"""
        self.videos.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_selected_video(self) -> Optional[Dict]:
        """获取选中的视频"""
        selection = self.tree.selection()
        if not selection:
            return None

        item = selection[0]
        values = self.tree.item(item, "values")
        if values:
            idx = int(values[0]) - 1
            if 0 <= idx < len(self.videos):
                return self.videos[idx]
        return None

    def get_all_videos(self) -> List[Dict]:
        """获取所有视频"""
        return self.videos.copy()


class DouyinGUIv2:
    """抖音自动化 GUI v2.0 - 单步操作模式"""

    def __init__(self):
        self.window = tk.Tk()
        self.window.title("抖音自动化工具 v2.0 - 单步操作模式")
        self.window.geometry("1200x800")

        # Playwright 相关
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False

        # 验证码监听器
        self.captcha_monitor: Optional[CaptchaMonitor] = None

        # 任务队列
        self.task_queue = queue.Queue()

        # 当前状态
        self.current_keyword = ""

        self._setup_ui()
        self._start_task_processor()

    def _setup_ui(self):
        """构建界面"""
        # 主容器
        main_container = ttk.Frame(self.window, padding="10")
        main_container.pack(fill="both", expand=True)

        # 左侧控制面板
        left_panel = ttk.Frame(main_container, width=350)
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
            parent,
            text="抖音自动化工具 v2.0",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # 1. 登录检测区域
        login_frame = ttk.LabelFrame(parent, text="1. 登录检测", padding="10")
        login_frame.pack(fill="x", pady=5)
        
        self.login_status_label = tk.Label(
            login_frame,
            text="● 未检测",
            font=("Arial", 10),
            fg="gray"
        )
        self.login_status_label.pack(anchor="w", pady=5)
        
        self.check_login_btn = ttk.Button(
            login_frame,
            text="检测登录状态",
            command=self._on_check_login
        )
        self.check_login_btn.pack(fill="x", pady=2)
        
        # 2. 搜索区域
        search_frame = ttk.LabelFrame(parent, text="2. 搜索视频", padding="10")
        search_frame.pack(fill="x", pady=5)
        
        tk.Label(search_frame, text="关键词:").pack(anchor="w")
        self.keyword_entry = ttk.Entry(search_frame)
        self.keyword_entry.pack(fill="x", pady=2)
        
        self.search_btn = ttk.Button(
            search_frame,
            text="一键搜索",
            command=self._on_search,
            state="disabled"
        )
        self.search_btn.pack(fill="x", pady=2)
        
        # 3. 筛选区域
        filter_frame = ttk.LabelFrame(parent, text="3. 筛选条件", padding="10")
        filter_frame.pack(fill="x", pady=5)
        
        self.filter_btn = ttk.Button(
            filter_frame,
            text="切换筛选（最多点赞 + 近七天）",
            command=self._on_apply_filter,
            state="disabled"
        )
        self.filter_btn.pack(fill="x", pady=2)
        
        # 4. 提取视频信息区域
        extract_frame = ttk.LabelFrame(parent, text="4. 提取视频信息", padding="10")
        extract_frame.pack(fill="x", pady=5)
        
        count_frame = ttk.Frame(extract_frame)
        count_frame.pack(fill="x", pady=2)
        
        tk.Label(count_frame, text="提取数量:").pack(side="left")
        self.extract_count_spinbox = ttk.Spinbox(
            count_frame,
            from_=1,
            to=50,
            width=10
        )
        self.extract_count_spinbox.set("20")
        self.extract_count_spinbox.pack(side="left", padx=5)
        
        self.extract_btn = ttk.Button(
            extract_frame,
            text="提取视频信息",
            command=self._on_extract_videos,
            state="disabled"
        )
        self.extract_btn.pack(fill="x", pady=2)
        
        # 5. 提取评论区域
        comment_frame = ttk.LabelFrame(parent, text="5. 提取评论", padding="10")
        comment_frame.pack(fill="x", pady=5)
        
        tk.Label(comment_frame, text="选择表格中的视频后点击提取").pack(anchor="w", pady=2)
        
        comment_count_frame = ttk.Frame(comment_frame)
        comment_count_frame.pack(fill="x", pady=2)
        
        tk.Label(comment_count_frame, text="评论数:").pack(side="left")
        self.comment_count_spinbox = ttk.Spinbox(
            comment_count_frame,
            from_=1,
            to=100,
            width=10
        )
        self.comment_count_spinbox.set("20")
        self.comment_count_spinbox.pack(side="left", padx=5)
        
        self.extract_comment_btn = ttk.Button(
            comment_frame,
            text="提取选中视频的评论",
            command=self._on_extract_comments,
            state="disabled"
        )
        self.extract_comment_btn.pack(fill="x", pady=2)
        
        # 状态指示器
        status_frame = ttk.LabelFrame(parent, text="操作状态", padding="10")
        status_frame.pack(fill="x", pady=5)
        
        self.status_text = tk.Text(
            status_frame,
            height=8,
            wrap=tk.WORD,
            font=("Consolas", 9)
        )
        self.status_text.pack(fill="both", expand=True)
        
        # 底部按钮
        bottom_frame = ttk.Frame(parent)
        bottom_frame.pack(fill="x", pady=10, side="bottom")
        
        self.clear_btn = ttk.Button(
            bottom_frame,
            text="清空数据",
            command=self._on_clear_data
        )
        self.clear_btn.pack(side="left", padx=2)
        
        self.quit_btn = ttk.Button(
            bottom_frame,
            text="退出",
            command=self._on_quit
        )
        self.quit_btn.pack(side="right", padx=2)
        
    def _setup_right_panel(self, parent):
        """构建右侧数据展示区"""
        # 标题
        title_frame = ttk.Frame(parent)
        title_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(
            title_frame,
            text="视频数据表格",
            font=("Arial", 12, "bold")
        ).pack(side="left")
        
        self.video_count_label = tk.Label(
            title_frame,
            text="共 0 条",
            font=("Arial", 10),
            fg="gray"
        )
        self.video_count_label.pack(side="right")
        
        # 视频表格
        self.video_table = VideoTableFrame(parent)
        self.video_table.pack(fill="both", expand=True)
        
    def _start_task_processor(self):
        """启动任务处理器（在主线程中处理队列任务）"""
        def process_tasks():
            try:
                if not self.task_queue.empty():
                    task = self.task_queue.get_nowait()
                    try:
                        task()
                    except Exception as e:
                        logger.error(f"[GUI] 任务执行失败: {e}")
                        logger.error(f"[GUI] 错误堆栈:\n{traceback.format_exc()}")
                        self._log_status(f"[错误] 操作失败: {str(e)}")
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
                self.browser = self.playwright.chromium.launch(headless=False)
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
                logger.info("[GUI] 浏览器初始化完成")
                
                # 自动加载本地Cookie
                self._auto_inject_cookies()
                
            except Exception as e:
                logger.error(f"[GUI] 浏览器初始化失败: {e}")
                logger.error(f"[GUI] 错误堆栈:\n{traceback.format_exc()}")
                raise
                
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
                
    # ========== 5个核心操作方法 ==========
    
    def _on_check_login(self):
        """1. 登录检测"""
        def task():
            try:
                self._log_status("=" * 50)
                self._log_status("正在检测登录状态...")
                self._init_browser()
                
                if self.page is None:
                    self._log_status("[失败] 浏览器初始化失败")
                    return
                
                # 注入本地Cookie
                from douyin.auth import inject_douyin_cookies_to_page, load_douyin_cookies
                from douyin.search import DouyinSearchManager
                
                cookies = load_douyin_cookies()
                if cookies:
                    self._log_status(f"[信息] 加载了 {len(cookies)} 个本地Cookie")
                    inject_douyin_cookies_to_page(self.page)
                else:
                    self._log_status("[信息] 未找到本地Cookie")
                
                # 打开首页并检查登录状态
                mgr = DouyinSearchManager(self.page)
                self._log_status("[信息] 正在打开抖音首页...")
                
                if not mgr.open_homepage():
                    self._log_status("[失败] 打开首页失败")
                    return
                
                self._log_status("[信息] 正在检查登录状态...")
                self.is_logged_in = mgr.check_login_status()
                
                if self.is_logged_in:
                    self._update_login_status("已登录", "green")
                    self._enable_buttons()
                    self._log_status("[成功] ✓ 检测完成：已登录")
                    self._log_status("[提示] 可以开始搜索视频了！")
                else:
                    self._update_login_status("未登录", "red")
                    self._log_status("[失败] ✗ 检测完成：未登录")
                    self._log_status("[提示] 请在浏览器中手动登录抖音")
                
                self._log_status("=" * 50)
                
                # 保存Cookie
                self._save_cookies()
                
            except Exception as e:
                logger.error(f"[GUI] 检测登录状态失败: {e}")
                self._log_status(f"[错误] 检测失败: {str(e)}")
        
        self.task_queue.put(task)
        
    def _on_search(self):
        """2. 一键搜索"""
        keyword = self.keyword_entry.get().strip()
        if not keyword:
            messagebox.showwarning("提示", "请输入搜索关键词")
            return
        
        def task():
            try:
                self._log_status("=" * 50)
                self._log_status(f"开始搜索: {keyword}")
                self.current_keyword = keyword
                
                if self.page is None:
                    self._log_status("[失败] 浏览器未初始化，请先检测登录状态")
                    return
                
                from douyin.search import DouyinSearchManager
                import random
                
                mgr = DouyinSearchManager(self.page)
                
                # 启动验证码监听
                self._start_captcha_monitor()
                
                # 定位搜索框
                self._log_status("[信息] 定位搜索框...")
                input_el = mgr._get_search_input_locator()
                input_el.wait_for(state="visible", timeout=10000)
                
                # 模拟输入
                self._log_status(f"[信息] 输入关键词: {keyword}")
                input_el.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.3, 0.6))
                input_el.click()
                time.sleep(random.uniform(0.2, 0.4))
                input_el.fill("")
                time.sleep(random.uniform(0.1, 0.3))
                input_el.type(keyword, delay=random.randint(80, 150))
                time.sleep(random.uniform(0.3, 0.6))
                
                # 点击搜索按钮
                self._log_status("[信息] 点击搜索按钮...")
                btn = mgr._get_search_btn_locator()
                if btn.count() == 0 or not btn.is_visible():
                    self._log_status("[失败] 未找到搜索按钮")
                    return
                
                btn.scroll_into_view_if_needed()
                time.sleep(random.uniform(0.2, 0.4))
                btn.click()
                
                # 等待页面加载
                wait_time = random.uniform(2.0, 3.0)
                self._log_status(f"[信息] 等待搜索结果加载...")
                time.sleep(wait_time)
                
                self._log_status(f"[成功] ✓ 搜索完成: {self.page.url}")
                self._log_status("[提示] 可以切换筛选条件或直接提取视频")
                self._log_status("=" * 50)
                
                # 保存Cookie
                self._save_cookies()
                
            except Exception as e:
                logger.error(f"[GUI] 搜索失败: {e}")
                self._log_status(f"[错误] 搜索失败: {str(e)}")
        
        self.task_queue.put(task)
        
    def _on_apply_filter(self):
        """3. 切换筛选"""
        def task():
            try:
                self._log_status("=" * 50)
                self._log_status("正在切换筛选条件...")
                
                if self.page is None:
                    self._log_status("[失败] 浏览器未初始化")
                    return
                
                from douyin.search import DouyinSearchManager
                
                mgr = DouyinSearchManager(self.page)
                
                # 启动验证码监听
                self._start_captcha_monitor()
                
                # 切换到视频标签
                self._log_status("[信息] 切换到视频标签...")
                if mgr._switch_to_video_tab():
                    self._log_status("[成功] ✓ 已切换到视频标签")
                else:
                    self._log_status("[警告] 切换视频标签失败，尝试继续")
                
                # 应用筛选：最多点赞 + 一周内
                self._log_status("[信息] 应用筛选条件（最多点赞 + 近七天）...")
                if mgr._apply_filters(sort_by="most_liked", time_range="week"):
                    self._log_status("[成功] ✓ 筛选条件已应用")
                else:
                    self._log_status("[警告] 应用筛选失败，使用默认排序")
                
                self._log_status("[提示] 可以开始提取视频信息了")
                self._log_status("=" * 50)
                
                # 保存Cookie
                self._save_cookies()
                
            except Exception as e:
                logger.error(f"[GUI] 切换筛选失败: {e}")
                self._log_status(f"[错误] 切换筛选失败: {str(e)}")
        
        self.task_queue.put(task)
        
    def _on_extract_videos(self):
        """4. 提取视频信息"""
        try:
            max_count = int(self.extract_count_spinbox.get())
        except ValueError:
            messagebox.showwarning("提示", "数量必须是数字")
            return
        
        def task():
            try:
                self._log_status("=" * 50)
                self._log_status(f"开始提取 {max_count} 个视频...")
                
                if self.page is None:
                    self._log_status("[失败] 浏览器未初始化")
                    return
                
                from douyin.search import DouyinSearchManager
                
                mgr = DouyinSearchManager(self.page)
                
                # 启动验证码监听
                self._start_captcha_monitor()
                
                # 提取视频信息
                self._log_status("[信息] 正在提取视频信息...")
                videos = mgr.get_current_page_videos(max_count)
                
                if videos:
                    # 清空表格
                    self.video_table.clear()
                    
                    # 添加到表格
                    for video in videos:
                        self.video_table.add_video(video)
                    
                    self._log_status(f"[成功] ✓ 成功提取 {len(videos)} 个视频")
                    self.video_count_label.config(text=f"共 {len(videos)} 条")
                    self._log_status("[提示] 选择视频后可以提取评论")
                else:
                    self._log_status("[失败] 未提取到视频")
                    self._log_status("[提示] 请检查搜索结果或重新搜索")
                
                self._log_status("=" * 50)
                
                # 保存Cookie
                self._save_cookies()
                
            except Exception as e:
                logger.error(f"[GUI] 提取视频失败

                
    # ========== 辅助方法 ==========
    
    def _start_captcha_monitor(self):
        """启动验证码监听（10秒后自动停止）"""
        if self.page:
            if self.captcha_monitor:
                self.captcha_monitor.stop()
            
            self.captcha_monitor = CaptchaMonitor(
                self.page,
                callback=self._log_status,
                auto_stop_seconds=10
            )
            self.captcha_monitor.start()
            self._log_status("[监听] 已启动验证码监听（10秒后自动停止）")
    
    def _log_status(self, message: str):
        """在状态区域显示消息"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_text.insert(tk.END, f"[{timestamp}] {message}
")
        self.status_text.see(tk.END)
        self.window.update()
    
    def _save_cookies(self):
        """保存Cookie（操作后调用）"""
        if self.context:
            try:
                from douyin.auth import save_douyin_cookies
                from datetime import datetime
                
                cookies = self.context.cookies()
                douyin_cookies = [
                    dict(c) for c in cookies 
                    if "douyin.com" in c.get("domain", "")
                ]
                
                if douyin_cookies:
                    save_douyin_cookies(
                        douyin_cookies,
                        meta={
                            "updated_at": datetime.now().isoformat(),
                            "source": "gui_v2_operation"
                        }
                    )
                    logger.info(f"[GUI] Cookie已保存: {len(douyin_cookies)} 个")
            except Exception as e:
                logger.error(f"[GUI] 保存Cookie失败: {e}")
    
    def _enable_buttons(self):
        """启用所有操作按钮"""
        self.search_btn.config(state="normal")
        self.filter_btn.config(state="normal")
        self.extract_btn.config(state="normal")
        self.extract_comment_btn.config(state="normal")
    
    def _update_login_status(self, text: str, color: str):
        """更新登录状态显示"""
        self.login_status_label.config(text=f"● {text}", fg=color)
    
    def _on_clear_data(self):
        """清空数据"""
        if messagebox.askyesno("确认", "确定要清空所有数据吗？"):
            self.video_table.clear()
            self.video_count_label.config(text="共 0 条")
            self.status_text.delete(1.0, tk.END)
            self._log_status("[信息] 数据已清空")
    
    def _on_quit(self):
        """退出程序"""
        if messagebox.askokcancel("退出", "确定要退出吗？"):
            self._cleanup()
            self.window.quit()
    
    def _cleanup(self):
        """清理资源"""
        try:
            logger.info("[GUI] 开始清理资源")
            
            # 停止验证码监听
            if self.captcha_monitor:
                self.captcha_monitor.stop()
            
            # 最后一次保存Cookie
            if self.context:
                self._save_cookies()
            
            # 关闭浏览器
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            
            logger.info("[GUI] 资源清理完成")
        except Exception as e:
            logger.warning(f"[GUI] 清理资源时出错: {e}")
    
    def run(self):
        """启动GUI"""
        try:
            logger.info("[GUI] 启动抖音自动化GUI v2.0")
            self.window.protocol("WM_DELETE_WINDOW", self._on_quit)
            self.window.mainloop()
        except Exception as e:
            logger.critical(f"[GUI] GUI运行失败: {e}")
            logger.critical(f"[GUI] 错误堆栈:
{traceback.format_exc()}")
            raise


def main():
    """启动抖音 GUI v2.0"""
    import argparse
    
    try:
        parser = argparse.ArgumentParser(description="抖音自动化GUI v2.0 - 单步操作模式")
        args = parser.parse_args()
        
        logger.info("=" * 60)
        logger.info("抖音自动化GUI v2.0启动")
        logger.info("=" * 60)
        
        app = DouyinGUIv2()
        app.run()
        
        logger.info("=" * 60)
        logger.info("抖音自动化GUI v2.0已退出")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.critical(f"程序启动失败: {e}")
        logger.critical(f"错误堆栈:
{traceback.format_exc()}")
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "启动失败", f"程序启动失败:

{e}

详细信息请查看日志文件"
            )
        except:
            pass
        
        raise


if __name__ == "__main__":
    main()
