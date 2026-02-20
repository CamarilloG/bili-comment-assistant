import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.dialogs import Querybox
from ttkbootstrap.scrolled import ScrolledFrame
import threading
import yaml
import json
import os
from loguru import logger
from playwright.sync_api import sync_playwright
from core.auth import AuthManager
import main as backend_main

class CommentTab(ttk.Frame):
    def __init__(self, master, config_file, **kwargs):
        super().__init__(master, **kwargs)
        self.config_file = config_file
        self.running = False
        
        # Variables
        self.img_path_var = tk.StringVar()
        self.enable_img_var = tk.BooleanVar(value=True)
        self.headless_var = tk.BooleanVar()
        self.browser_path_var = tk.StringVar()
        self.browser_port_var = tk.IntVar(value=0)
        
        self.sort_var = tk.StringVar(value="totalrank")
        self.duration_var = tk.IntVar(value=0)
        self.strategy_var = tk.StringVar(value="order")
        self.strict_match_var = tk.BooleanVar(value=False)
        self.progress_var = tk.StringVar(value="就绪")
        self.time_filter_var = tk.StringVar(value="none")
        
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        # Main Paned Window (Split Left/Right)
        self.paned = ttk.Panedwindow(self, orient=HORIZONTAL)
        self.paned.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # --- LEFT PANEL: Configuration ---
        left_panel = ttk.Frame(self.paned)
        self.paned.add(left_panel, weight=2)

        # 1. Action bar (fixed at top, same row: start / stop / status)
        action_bar = ttk.Frame(left_panel)
        action_bar.pack(side=TOP, fill=X, pady=(0, 10))
        self.start_btn = ttk.Button(action_bar, text="保存并开始", command=self.start_task, bootstyle="success", width=14)
        self.start_btn.pack(side=LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(action_bar, text="停止", command=self.stop_task, bootstyle="danger", state="disabled", width=10)
        self.stop_btn.pack(side=LEFT, padx=(0, 12))
        ttk.Label(action_bar, textvariable=self.progress_var, bootstyle="info", font=("", 10)).pack(side=LEFT)

        # 2. Scrollable Configuration Area
        config_scroll = ScrolledFrame(left_panel, autohide=True)
        config_scroll.pack(side=TOP, fill=BOTH, expand=YES)
        
        # Use config_scroll.container as the parent for config groups but we need to reference config_scroll directly for packing
        # Actually in ttkbootstrap ScrolledFrame, we pack items into it directly and it handles the container? 
        # No, checking docs: ScrolledFrame is a frame, we pack into it. 
        # Let's verify behavior. Typically we pack into `scroll_frame` itself or a property.
        # Looking at common usage: `sf = ScrolledFrame(...)`, `sub_widget.pack(in_=sf)`.
        # However, typically ScrolledFrame acts as the parent widget.
        
        config_content = config_scroll

        # 1. Basic Config
        basic_group = ttk.Labelframe(config_content, text="基础配置", padding=12)
        basic_group.pack(fill=X, pady=8, padx=2)
        
        ttk.Label(basic_group, text="搜索关键词 (逗号分隔):").pack(anchor=W)
        self.keywords_entry = ttk.Entry(basic_group)
        self.keywords_entry.pack(fill=X, pady=3)
        
        ttk.Label(basic_group, text="评论内容 (固定单条):").pack(anchor=W)
        self.comment_text = ttk.Text(basic_group, height=5)
        self.comment_text.pack(fill=X, pady=3)
        
        img_frame = ttk.Frame(basic_group)
        img_frame.pack(fill=X, pady=3)
        ttk.Checkbutton(img_frame, text="启用图片", variable=self.enable_img_var, bootstyle="round-toggle").pack(side=LEFT)
        ttk.Label(img_frame, text="路径:").pack(side=LEFT, padx=(10, 5))
        self.img_entry = ttk.Entry(img_frame, textvariable=self.img_path_var)
        self.img_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        ttk.Button(img_frame, text="...", width=4, command=self.select_image).pack(side=RIGHT)

        # 2. Parameters
        param_group = ttk.Labelframe(config_content, text="运行参数", padding=12)
        param_group.pack(fill=X, pady=8, padx=2)
        
        # Use Grid for better alignment
        param_group.columnconfigure(1, weight=1)
        param_group.columnconfigure(3, weight=1)
        
        ttk.Label(param_group, text="间隔(s):").grid(row=0, column=0, sticky=W)
        
        delay_frame = ttk.Frame(param_group)
        delay_frame.grid(row=0, column=1, sticky=EW, padx=5)
        self.min_delay = ttk.Entry(delay_frame, width=5)
        self.min_delay.pack(side=LEFT, fill=X, expand=YES)
        ttk.Label(delay_frame, text="-").pack(side=LEFT, padx=2)
        self.max_delay = ttk.Entry(delay_frame, width=5)
        self.max_delay.pack(side=LEFT, fill=X, expand=YES)
        
        ttk.Label(param_group, text="超时(ms):").grid(row=0, column=2, sticky=W, padx=(10, 0))
        self.timeout_entry = ttk.Entry(param_group, width=8)
        self.timeout_entry.grid(row=0, column=3, sticky=EW, padx=5)
        
        ttk.Label(param_group, text="最大评论数:").grid(row=1, column=0, sticky=W, pady=5)
        self.max_videos = ttk.Entry(param_group, width=8)
        self.max_videos.grid(row=1, column=1, sticky=EW, padx=5, pady=5)
        
        ttk.Checkbutton(param_group, text="显示窗口", variable=self.headless_var, onvalue=False, offvalue=True).grid(row=1, column=2, columnspan=2, sticky=W, padx=10)

        # 3. Search Filters
        filter_group = ttk.Labelframe(config_content, text="综合设置", padding=12)
        filter_group.pack(fill=X, pady=8, padx=2)
        
        filter_group.columnconfigure(1, weight=1)
        filter_group.columnconfigure(3, weight=1)

        ttk.Label(filter_group, text="排序:").grid(row=0, column=0, sticky=W)
        self.sort_map = {"综合排序": "totalrank", "最新发布": "pubdate", "最多播放": "click", "最多弹幕": "dm", "最多收藏": "stow"}
        self.sort_map_rev = {v: k for k, v in self.sort_map.items()}
        self.sort_cb = ttk.Combobox(filter_group, values=list(self.sort_map.keys()), state="readonly")
        self.sort_cb.grid(row=0, column=1, sticky=EW, padx=5, pady=2)
        self.sort_cb.current(0)
        
        ttk.Label(filter_group, text="时长:").grid(row=0, column=2, sticky=W, padx=(10, 0))
        self.dur_map = {"全部时长": 0, "10分钟以下": 1, "10-30分钟": 2, "30-60分钟": 3, "60分钟以上": 4}
        self.dur_map_rev = {v: k for k, v in self.dur_map.items()}
        self.dur_cb = ttk.Combobox(filter_group, values=list(self.dur_map.keys()), state="readonly")
        self.dur_cb.grid(row=0, column=3, sticky=EW, padx=5, pady=2)
        self.dur_cb.current(0)

        ttk.Label(filter_group, text="策略:").grid(row=1, column=0, sticky=W)
        self.strat_map = {"顺序选择": "order", "随机选择": "random"}
        self.strat_map_rev = {v: k for k, v in self.strat_map.items()}
        self.strat_cb = ttk.Combobox(filter_group, values=list(self.strat_map.keys()), state="readonly")
        self.strat_cb.grid(row=1, column=1, sticky=EW, padx=5, pady=2)
        self.strat_cb.current(0)

        ttk.Checkbutton(filter_group, text="严格匹配 (标题含关键词)", variable=self.strict_match_var, onvalue=True, offvalue=False).grid(row=1, column=2, columnspan=2, sticky=W, padx=10)
        
        ttk.Label(filter_group, text="时间限制:").grid(row=2, column=0, sticky=W, pady=2)
        self.time_filter_cb = ttk.Combobox(filter_group, textvariable=self.time_filter_var, values=["不限制", "近几天", "指定日期范围"], state="readonly")
        self.time_filter_cb.grid(row=2, column=1, sticky=EW, padx=5, pady=2)
        self.time_filter_cb.bind("<<ComboboxSelected>>", self.on_time_filter_change)
        
        self.date_input_frame = ttk.Frame(filter_group)
        self.date_input_frame.grid(row=2, column=2, columnspan=2, sticky=EW, padx=5)
        
        self.recent_days_frame = ttk.Frame(self.date_input_frame)
        ttk.Label(self.recent_days_frame, text="最近").pack(side=LEFT)
        self.recent_days_entry = ttk.Entry(self.recent_days_frame, width=5)
        self.recent_days_entry.insert(0, "1")
        self.recent_days_entry.pack(side=LEFT, padx=2, fill=X, expand=YES)
        ttk.Label(self.recent_days_frame, text="天").pack(side=LEFT)
        
        self.date_range_frame = ttk.Frame(self.date_input_frame)
        self.date_start_entry = ttk.Entry(self.date_range_frame, width=9)
        self.date_start_entry.pack(side=LEFT, padx=2, fill=X, expand=YES)
        ttk.Button(self.date_range_frame, text="📅", width=2, command=self.pick_start_date, bootstyle="info-outline").pack(side=LEFT)
        ttk.Label(self.date_range_frame, text="-").pack(side=LEFT, padx=2)
        self.date_end_entry = ttk.Entry(self.date_range_frame, width=9)
        self.date_end_entry.pack(side=LEFT, padx=2, fill=X, expand=YES)
        ttk.Button(self.date_range_frame, text="📅", width=2, command=self.pick_end_date, bootstyle="info-outline").pack(side=LEFT)
        
        # 4. Browser & Account (one card: browser path row, then port + debug + account row)
        browser_group = ttk.Labelframe(config_content, text="浏览器与账号", padding=12)
        browser_group.pack(fill=X, pady=8, padx=2)
        browser_group.columnconfigure(1, weight=1)
        ttk.Label(browser_group, text="Exe路径:").grid(row=0, column=0, sticky=W, pady=2)
        br_path_frame = ttk.Frame(browser_group)
        br_path_frame.grid(row=0, column=1, columnspan=3, sticky=EW, padx=5, pady=2)
        ttk.Entry(br_path_frame, textvariable=self.browser_path_var).pack(side=LEFT, fill=X, expand=YES)
        ttk.Button(br_path_frame, text="...", width=4, command=self.select_browser).pack(side=RIGHT, padx=(5, 0))
        ttk.Label(browser_group, text="调试端口:").grid(row=1, column=0, sticky=W, pady=3)
        ttk.Entry(browser_group, textvariable=self.browser_port_var, width=10).grid(row=1, column=1, sticky=W, padx=5, pady=3)
        ttk.Button(browser_group, text="开启调试模式", command=self.toggle_debug_server, bootstyle="info-outline", width=12).grid(row=1, column=2, sticky=W, padx=5, pady=3)
        account_row = ttk.Frame(browser_group)
        account_row.grid(row=2, column=0, columnspan=4, sticky=W, pady=6)
        self.status_label = ttk.Label(account_row, text="未检测", bootstyle="secondary")
        self.status_label.pack(side=LEFT, padx=(0, 8))
        ttk.Button(account_row, text="检测", command=self.check_login_status, bootstyle="warning-outline", width=8).pack(side=LEFT, padx=2)
        ttk.Button(account_row, text="扫码", command=self.qr_login, bootstyle="primary-outline", width=8).pack(side=LEFT, padx=2)

        # --- RIGHT PANEL: Results & Logs ---
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        list_frame = ttk.Labelframe(right_frame, text="视频处理列表", padding=12)
        list_frame.pack(fill=BOTH, expand=YES, pady=8)
        
        cols = ("bv", "title", "author", "date", "views", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse", bootstyle="info")
        
        for col in cols:
            self.tree.heading(col, text=col.capitalize(), command=lambda c=col: self.sort_tree(c, False))
        
        self.tree.heading("bv", text="BV号")
        self.tree.heading("title", text="标题")
        self.tree.heading("author", text="UP主")
        self.tree.heading("date", text="日期")
        self.tree.heading("views", text="播放")
        self.tree.heading("status", text="状态")
        
        # Adaptive column width
        self.tree.column("bv", width=100, minwidth=80)
        self.tree.column("title", width=250, minwidth=150)
        self.tree.column("author", width=120, minwidth=80)
        self.tree.column("date", width=100, minwidth=80)
        self.tree.column("views", width=80, minwidth=60)
        self.tree.column("status", width=80, minwidth=60)
        
        scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=RIGHT, fill=Y)

        self.tree_menu = tk.Menu(self, tearoff=0)
        self.tree_menu.add_command(label="复制 BV 号", command=self.copy_bv)
        self.tree_menu.add_command(label="复制 标题", command=self.copy_title)
        self.tree.bind("<Button-3>", self.show_context_menu)

        log_frame = ttk.Labelframe(right_frame, text="运行日志", padding=12)
        log_frame.pack(fill=BOTH, expand=YES, pady=8)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state='normal')
        self.log_area.pack(fill=BOTH, expand=YES)

    def on_time_filter_change(self, event=None):
        selection = self.time_filter_cb.get()
        self.recent_days_frame.pack_forget()
        self.date_range_frame.pack_forget()
        if selection == "近几天":
            self.recent_days_frame.pack(fill=X, padx=5)
        elif selection == "指定日期范围":
            self.date_range_frame.pack(fill=X, padx=5)

    def pick_start_date(self):
        date = Querybox.get_date(parent=self, title="选择开始日期")
        if date:
            self.date_start_entry.delete(0, tk.END)
            self.date_start_entry.insert(0, date.strftime("%Y-%m-%d"))

    def pick_end_date(self):
        date = Querybox.get_date(parent=self, title="选择结束日期")
        if date:
            self.date_end_entry.delete(0, tk.END)
            self.date_end_entry.insert(0, date.strftime("%Y-%m-%d"))

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f)
            
            search = conf.get('search', {})
            keywords = ",".join(search.get('keywords', []))
            self.keywords_entry.insert(0, keywords)
            self.max_videos.insert(0, search.get('max_videos_per_keyword', 5))
            
            comment = conf.get('comment', {})
            texts = comment.get('texts', [])
            if texts: self.comment_text.insert("1.0", texts[0])
            self.enable_img_var.set(comment.get('enable_image', True))
            images = comment.get('images', [])
            if images: self.img_path_var.set(images[0])
            
            behavior = conf.get('behavior', {})
            self.min_delay.insert(0, behavior.get('min_delay', 5))
            self.max_delay.insert(0, behavior.get('max_delay', 15))
            self.timeout_entry.insert(0, behavior.get('timeout', 30000))
            self.headless_var.set(behavior.get('headless', False))
            
            browser = conf.get('browser', {})
            self.browser_path_var.set(browser.get('path', ''))
            self.browser_port_var.set(browser.get('port', 0))
            
            filters = search.get('filter', {})
            sort_val = filters.get('sort', 'totalrank')
            if sort_val in self.sort_map_rev: self.sort_cb.set(self.sort_map_rev[sort_val])
            dur_val = filters.get('duration', 0)
            if dur_val in self.dur_map_rev: self.dur_cb.set(self.dur_map_rev[dur_val])
            
            strategy = search.get('strategy', {})
            strat_val = strategy.get('selection', 'order')
            if strat_val in self.strat_map_rev: self.strat_cb.set(self.strat_map_rev[strat_val])
            self.strict_match_var.set(strategy.get('strict_title_match', False))
            
            time_filter = filters.get('time_range', {})
            t_type = time_filter.get('type', 'none')
            t_map = {"none": "不限制", "recent": "近几天", "range": "指定日期范围"}
            if t_type in t_map: self.time_filter_cb.set(t_map[t_type])
            if t_type == "recent":
                self.recent_days_entry.delete(0, tk.END)
                self.recent_days_entry.insert(0, str(time_filter.get('value', 1)))
            elif t_type == "range":
                val = time_filter.get('value', {})
                if val.get('start'): self.date_start_entry.delete(0, tk.END); self.date_start_entry.insert(0, val['start'])
                if val.get('end'): self.date_end_entry.delete(0, tk.END); self.date_end_entry.insert(0, val['end'])
            self.on_time_filter_change()
        except Exception as e:
            logger.error(f"Config Load Error: {e}")

    def save_config(self):
        try:
            keywords = [k.strip() for k in self.keywords_entry.get().split(",") if k.strip()]
            if not keywords:
                messagebox.showerror("错误", "请输入关键词")
                return False
            comment_txt = self.comment_text.get("1.0", tk.END).strip()
            if not comment_txt:
                messagebox.showerror("错误", "请输入评论内容")
                return False
            
            t_selection = self.time_filter_cb.get()
            time_filter = {"type": "none", "value": None}
            if t_selection == "近几天":
                days = int(self.recent_days_entry.get())
                time_filter = {"type": "recent", "value": days}
            elif t_selection == "指定日期范围":
                start = self.date_start_entry.get()
                end = self.date_end_entry.get()
                time_filter = {"type": "range", "value": {"start": start, "end": end}}

            # Load existing config to preserve other sections
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    conf = yaml.safe_load(f) or {}
            else:
                conf = {}

            conf.update({
                "account": {"cookie_file": "cookies.json"},
                "search": {
                    "keywords": keywords,
                    "max_videos_per_keyword": int(self.max_videos.get()),
                    "filter": {
                        "sort": self.sort_map.get(self.sort_cb.get(), "totalrank"),
                        "duration": self.dur_map.get(self.dur_cb.get(), 0),
                        "time_range": time_filter
                    },
                    "strategy": {
                        "selection": self.strat_map.get(self.strat_cb.get(), "order"),
                        "strict_title_match": self.strict_match_var.get(),
                        "random_pool_size": 20
                    }
                },
                "comment": {
                    "enable_image": self.enable_img_var.get(),
                    "texts": [comment_txt],
                    "images": [self.img_path_var.get()] if self.img_path_var.get() else []
                },
                "behavior": {
                    "min_delay": float(self.min_delay.get()),
                    "max_delay": float(self.max_delay.get()),
                    "headless": self.headless_var.get(),
                    "timeout": int(self.timeout_entry.get())
                },
                "browser": {
                    "path": self.browser_path_var.get(),
                    "port": self.browser_port_var.get()
                }
            })
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(conf, f, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            return False

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image", "*.jpg *.png *.jpeg")])
        if path: self.img_path_var.set(path)

    def select_browser(self):
        path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe")])
        if path: self.browser_path_var.set(path)

    def start_task(self):
        if not self.save_config(): return
        if self.running: return
        for item in self.tree.get_children(): self.tree.delete(item)
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set("任务运行中...")
        logger.info("任务已启动...")
        t = threading.Thread(target=self._run_backend)
        t.daemon = True
        t.start()

    def stop_task(self):
        if self.running:
            logger.info("正在停止...")
            self.progress_var.set("正在停止...")
            backend_main.stop_task()
            self.stop_btn.config(state="disabled")

    def sort_tree(self, col, reverse):
        l = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]
        def try_int(val):
            try: return int(val.replace("万", "0000").replace("+", ""))
            except: return val
        try: l.sort(key=lambda t: try_int(t[0]), reverse=reverse)
        except: l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l): self.tree.move(k, '', index)
        self.tree.heading(col, command=lambda: self.sort_tree(col, not reverse))

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.tree_menu.post(event.x_root, event.y_root)

    def copy_bv(self):
        item = self.tree.selection()
        if item:
            val = self.tree.item(item[0])['values'][0]
            self.clipboard_clear()
            self.clipboard_append(val)

    def copy_title(self):
        item = self.tree.selection()
        if item:
            val = self.tree.item(item[0])['values'][1]
            self.clipboard_clear()
            self.clipboard_append(val)

    def update_video_list(self, video_info):
        def _update():
            found = False
            for item in self.tree.get_children():
                if self.tree.item(item)['values'][0] == video_info.get('bv'):
                    found = True
                    break
            if not found:
                tags = ('even',) if len(self.tree.get_children()) % 2 == 0 else ('odd',)
                self.tree.insert("", "end", values=(
                    video_info.get('bv', ''),
                    video_info.get('title', 'Unknown'),
                    video_info.get('author', 'Unknown'),
                    video_info.get('date', ''),
                    video_info.get('views', ''),
                    "Pending"
                ), tags=tags)
        self.tree.tag_configure('odd', background='#F0F0F0')
        self.tree.tag_configure('even', background='#FFFFFF')
        self.after(0, _update)

    def update_video_status(self, bvid, status):
        def _update():
            for item in self.tree.get_children():
                if self.tree.item(item)['values'][0] == bvid:
                    vals = list(self.tree.item(item)['values'])
                    vals[5] = status
                    self.tree.item(item, values=vals)
                    break
        self.after(0, _update)

    def _run_backend(self):
        try:
            backend_main.main(
                video_callback=self.update_video_list,
                status_callback=self.update_video_status
            )
            self.after(0, lambda: self.progress_var.set("任务完成"))
        except Exception as e:
            logger.error(f"任务异常: {e}")
            self.after(0, lambda: self.progress_var.set("任务异常"))
        finally:
            self.running = False
            self.after(0, lambda: self.start_btn.config(state="normal"))
            self.after(0, lambda: self.stop_btn.config(state="disabled"))
            logger.info("任务结束。")

    def toggle_debug_server(self):
        """Start debug API server on demand; show message if already running."""
        if backend_main.is_api_server_started():
            messagebox.showinfo("调试模式", "调试服务已在运行：http://localhost:8000")
            return
        backend_main.start_api_server()
        messagebox.showinfo("调试模式", "调试服务已启动：http://localhost:8000")

    def check_login_status(self):
        threading.Thread(target=self._check_login_thread, daemon=True).start()

    def _check_login_thread(self):
        self.after(0, lambda: self.status_label.config(text="检测中...", bootstyle="secondary"))
        try:
            # Load config to get browser args
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f) or {}
            
            launch_args = backend_main.get_browser_launch_args(conf)
            if not launch_args:
                self.after(0, lambda: self.status_label.config(text="配置错误", bootstyle="danger"))
                return

            with sync_playwright() as p:
                # launch_args already contains executable_path and args
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                auth = AuthManager(context, "cookies.json")
                if os.path.exists("cookies.json"):
                    with open("cookies.json", 'r', encoding='utf-8') as f:
                        context.add_cookies(json.load(f))
                is_logged_in = auth._check_login_status()
                browser.close()
                if is_logged_in:
                    self.after(0, lambda: self.status_label.config(text="已登录", bootstyle="success"))
                    logger.info("已登录")
                else:
                    self.after(0, lambda: self.status_label.config(text="未登录", bootstyle="danger"))
                    logger.warning("未登录")
        except Exception as e:
            logger.error(f"检测失败: {e}")
            self.after(0, lambda: self.status_label.config(text="出错", bootstyle="danger"))

    def qr_login(self):
        threading.Thread(target=self._qr_login_thread, daemon=True).start()

    def _qr_login_thread(self):
        try:
            # Load config to get browser args
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f) or {}
            
            launch_args = backend_main.get_browser_launch_args(conf, force_headed=True)
            if not launch_args:
                messagebox.showerror("错误", "浏览器配置错误")
                return

            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_args)
                context = browser.new_context()
                auth = AuthManager(context, "cookies.json")
                if auth._qr_login():
                    self.after(0, lambda: self.status_label.config(text="已登录", bootstyle="success"))
                    messagebox.showinfo("成功", "登录成功")
                else:
                    messagebox.showwarning("失败", "登录失败")
                browser.close()
        except Exception as e:
            logger.error(f"登录出错: {e}")
