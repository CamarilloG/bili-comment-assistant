import sys
import threading
import yaml
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from loguru import logger
from playwright.sync_api import sync_playwright

# Import core modules
from core.auth import AuthManager
import main as backend_main

from ttkbootstrap.dialogs import Querybox

# Redirect logs to GUI
class TextHandler:
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)

    def flush(self):
        pass

class BiliBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bilibili 自动评论助手")
        self.root.geometry("1100x800") # Increased size for 2 columns
        self.config_file = "config.yaml"
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
        
        # UI Setup
        self.setup_ui()
        self.load_config()
        
        # Log redirection
        logger.remove()
        logger.add(TextHandler(self.log_area), format="{time:HH:mm:ss} | {message}")

    def setup_ui(self):
        # Main Paned Window (Split Left/Right)
        self.paned = ttk.Panedwindow(self.root, orient=HORIZONTAL)
        self.paned.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # --- LEFT PANEL: Configuration ---
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1) # weight 1 implies it takes less space if right is larger
        
        # Scrollable Left Panel (Optional, but good for many configs)
        # For simplicity, we stick to packed frames.
        
        # 1. Basic Config
        basic_group = ttk.Labelframe(left_frame, text="基础配置", padding=5)
        basic_group.pack(fill=X, pady=2)
        
        ttk.Label(basic_group, text="搜索关键词 (逗号分隔):").pack(anchor=W)
        self.keywords_entry = ttk.Entry(basic_group)
        self.keywords_entry.pack(fill=X, pady=2)
        
        ttk.Label(basic_group, text="评论内容 (固定单条):").pack(anchor=W)
        self.comment_text = ttk.Text(basic_group, height=3)
        self.comment_text.pack(fill=X, pady=2)
        
        # Image Config
        img_frame = ttk.Frame(basic_group)
        img_frame.pack(fill=X, pady=2)
        
        ttk.Checkbutton(img_frame, text="启用图片", variable=self.enable_img_var, bootstyle="round-toggle").pack(side=LEFT)
        
        ttk.Label(img_frame, text="路径:").pack(side=LEFT, padx=(10, 0))
        self.img_entry = ttk.Entry(img_frame, textvariable=self.img_path_var)
        self.img_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        ttk.Button(img_frame, text="...", width=3, command=self.select_image).pack(side=RIGHT)

        # 2. Parameters
        param_group = ttk.Labelframe(left_frame, text="运行参数", padding=5)
        param_group.pack(fill=X, pady=2)
        
        r1 = ttk.Frame(param_group)
        r1.pack(fill=X, pady=2)
        ttk.Label(r1, text="间隔(s):").pack(side=LEFT)
        self.min_delay = ttk.Entry(r1, width=4)
        self.min_delay.pack(side=LEFT, padx=2)
        ttk.Label(r1, text="-").pack(side=LEFT)
        self.max_delay = ttk.Entry(r1, width=4)
        self.max_delay.pack(side=LEFT, padx=2)
        
        ttk.Label(r1, text="超时(ms):").pack(side=LEFT, padx=(10, 2))
        self.timeout_entry = ttk.Entry(r1, width=6)
        self.timeout_entry.pack(side=LEFT)
        
        r2 = ttk.Frame(param_group)
        r2.pack(fill=X, pady=2)
        ttk.Label(r2, text="最大评论数:").pack(side=LEFT)
        self.max_videos = ttk.Entry(r2, width=6)
        self.max_videos.pack(side=LEFT, padx=5)
        
        ttk.Checkbutton(r2, text="显示窗口", variable=self.headless_var, onvalue=False, offvalue=True).pack(side=LEFT, padx=10)

        # 3. Search Filters
        filter_group = ttk.Labelframe(left_frame, text="综合设置", padding=5)
        filter_group.pack(fill=X, pady=2)
        
        fr1 = ttk.Frame(filter_group)
        fr1.pack(fill=X, pady=2)
        
        self.sort_map = {"综合排序": "totalrank", "最新发布": "pubdate", "最多播放": "click", "最多弹幕": "dm", "最多收藏": "stow"}
        self.sort_map_rev = {v: k for k, v in self.sort_map.items()}
        # Use a separate variable for Combobox display value, not sharing with internal logic variable if possible, 
        # OR ensure we only store the Display Value in the widget, and map it when saving.
        # Current implementation binds textvariable=self.sort_var. 
        # But we also bind <<ComboboxSelected>> to update self.sort_var with the English value? 
        # Wait, line 129: lambda e: self.sort_var.set(self.sort_map[self.sort_cb.get()])
        # This overwrites the Combobox's text variable with "totalrank" (English) which is then displayed!
        # FIX: Remove textvariable binding or use a separate variable for the underlying value.
        # Best approach: Don't use textvariable for the Combobox if we want to display Chinese but store English.
        # Just use .get() and .set().
        
        self.sort_cb = ttk.Combobox(fr1, values=list(self.sort_map.keys()), state="readonly", width=9)
        self.sort_cb.pack(side=LEFT, padx=2)
        # self.sort_cb.bind("<<ComboboxSelected>>", ...) -> No need to update a var immediately if we read from CB on save
        self.sort_cb.current(0) # Default
        
        self.dur_map = {"全部时长": 0, "10分钟以下": 1, "10-30分钟": 2, "30-60分钟": 3, "60分钟以上": 4}
        self.dur_map_rev = {v: k for k, v in self.dur_map.items()}
        self.dur_cb = ttk.Combobox(fr1, values=list(self.dur_map.keys()), state="readonly", width=9)
        self.dur_cb.pack(side=LEFT, padx=2)
        self.dur_cb.current(0)

        fr2 = ttk.Frame(filter_group)
        fr2.pack(fill=X, pady=2)
        ttk.Label(fr2, text="策略:").pack(side=LEFT)
        self.strat_map = {"顺序选择": "order", "随机选择": "random"}
        self.strat_map_rev = {v: k for k, v in self.strat_map.items()}
        self.strat_cb = ttk.Combobox(fr2, values=list(self.strat_map.keys()), state="readonly", width=10)
        self.strat_cb.pack(side=LEFT, padx=5)
        self.strat_cb.current(0)

        # Strict Match Checkbox
        fr3 = ttk.Frame(filter_group)
        fr3.pack(fill=X, pady=2)
        ttk.Checkbutton(fr3, text="严格匹配模式 (标题包含关键词)", variable=self.strict_match_var, onvalue=True, offvalue=False).pack(side=LEFT)
        
        # Date Filter
        fr4 = ttk.Frame(filter_group)
        fr4.pack(fill=X, pady=2)
        ttk.Label(fr4, text="时间限制:").pack(side=LEFT)
        
        self.time_filter_var = tk.StringVar(value="none")
        self.time_filter_cb = ttk.Combobox(fr4, textvariable=self.time_filter_var, values=["不限制", "近几天", "指定日期范围"], state="readonly", width=12)
        self.time_filter_cb.pack(side=LEFT, padx=5)
        self.time_filter_cb.bind("<<ComboboxSelected>>", self.on_time_filter_change)
        
        # Dynamic Frames for Date Inputs
        self.date_input_frame = ttk.Frame(filter_group)
        self.date_input_frame.pack(fill=X, pady=2)
        
        # Recent X Days
        self.recent_days_frame = ttk.Frame(self.date_input_frame)
        ttk.Label(self.recent_days_frame, text="最近").pack(side=LEFT)
        self.recent_days_entry = ttk.Entry(self.recent_days_frame, width=5)
        self.recent_days_entry.insert(0, "1")
        self.recent_days_entry.pack(side=LEFT, padx=2)
        ttk.Label(self.recent_days_frame, text="天").pack(side=LEFT)
        
        # Date Range
        self.date_range_frame = ttk.Frame(self.date_input_frame)
        ttk.Label(self.date_range_frame, text="从").pack(side=LEFT)
        
        self.date_start_entry = ttk.Entry(self.date_range_frame, width=10)
        self.date_start_entry.pack(side=LEFT, padx=2)
        ttk.Button(self.date_range_frame, text="📅", width=2, command=self.pick_start_date, bootstyle="info-outline").pack(side=LEFT)
        
        ttk.Label(self.date_range_frame, text="到").pack(side=LEFT, padx=(5, 0))
        
        self.date_end_entry = ttk.Entry(self.date_range_frame, width=10)
        self.date_end_entry.pack(side=LEFT, padx=2)
        ttk.Button(self.date_range_frame, text="📅", width=2, command=self.pick_end_date, bootstyle="info-outline").pack(side=LEFT)
        
        # 4. Browser Config (New)
        browser_group = ttk.Labelframe(left_frame, text="浏览器配置 (高级)", padding=5)
        browser_group.pack(fill=X, pady=2)
        
        br1 = ttk.Frame(browser_group)
        br1.pack(fill=X, pady=2)
        ttk.Label(br1, text="Exe路径:").pack(side=LEFT)
        ttk.Entry(br1, textvariable=self.browser_path_var).pack(side=LEFT, fill=X, expand=YES, padx=5)
        ttk.Button(br1, text="...", width=3, command=self.select_browser).pack(side=RIGHT)
        
        br2 = ttk.Frame(browser_group)
        br2.pack(fill=X, pady=2)
        ttk.Label(br2, text="调试端口:").pack(side=LEFT)
        ttk.Entry(br2, textvariable=self.browser_port_var, width=10).pack(side=LEFT, padx=5)
        ttk.Label(br2, text="(0为不使用)").pack(side=LEFT)

        # 5. Account
        auth_group = ttk.Labelframe(left_frame, text="账号状态", padding=5)
        auth_group.pack(fill=X, pady=2)
        self.status_label = ttk.Label(auth_group, text="未检测", bootstyle="secondary")
        self.status_label.pack(side=LEFT, padx=10)
        ttk.Button(auth_group, text="检测", command=self.check_login_status, bootstyle="warning-outline", width=6).pack(side=LEFT, padx=2)
        ttk.Button(auth_group, text="扫码", command=self.qr_login, bootstyle="primary", width=6).pack(side=LEFT, padx=2)

        # 6. Control
        ctrl_frame = ttk.Frame(left_frame)
        ctrl_frame.pack(fill=X, pady=10)
        self.start_btn = ttk.Button(ctrl_frame, text="保存并开始", command=self.start_task, bootstyle="success")
        self.start_btn.pack(fill=X, pady=2)
        self.stop_btn = ttk.Button(ctrl_frame, text="停止", command=self.stop_task, bootstyle="danger", state="disabled")
        self.stop_btn.pack(fill=X, pady=2)
        ttk.Label(ctrl_frame, textvariable=self.progress_var, bootstyle="info").pack(fill=X, pady=5)

        # --- RIGHT PANEL: Results & Logs ---
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        # Video List
        list_frame = ttk.Labelframe(right_frame, text="视频处理列表", padding=5)
        list_frame.pack(fill=BOTH, expand=YES, pady=2)
        
        cols = ("bv", "title", "author", "date", "views", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", selectmode="browse", bootstyle="info")
        
        # Configure columns with sorting
        self.tree.heading("bv", text="BV号", command=lambda: self.sort_tree("bv", False))
        self.tree.heading("title", text="标题", command=lambda: self.sort_tree("title", False))
        self.tree.heading("author", text="UP主", command=lambda: self.sort_tree("author", False))
        self.tree.heading("date", text="日期", command=lambda: self.sort_tree("date", False))
        self.tree.heading("views", text="播放", command=lambda: self.sort_tree("views", False))
        self.tree.heading("status", text="状态", command=lambda: self.sort_tree("status", False))
        
        self.tree.column("bv", width=100)
        self.tree.column("title", width=200)
        self.tree.column("author", width=100)
        self.tree.column("date", width=80)
        self.tree.column("views", width=60)
        self.tree.column("status", width=60)
        
        scroll = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        
        self.tree.pack(side=LEFT, fill=BOTH, expand=YES)
        scroll.pack(side=RIGHT, fill=Y)

        # Context Menu
        self.tree_menu = tk.Menu(self.root, tearoff=0)
        self.tree_menu.add_command(label="复制 BV 号", command=self.copy_bv)
        self.tree_menu.add_command(label="复制 标题", command=self.copy_title)
        self.tree.bind("<Button-3>", self.show_context_menu)

        # Logs
        log_frame = ttk.Labelframe(right_frame, text="运行日志", padding=5)
        log_frame.pack(fill=BOTH, expand=YES, pady=2) # Split space with list
        
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
        date = Querybox.get_date(parent=self.date_range_frame, title="选择开始日期")
        if date:
            self.date_start_entry.delete(0, tk.END)
            self.date_start_entry.insert(0, date.strftime("%Y-%m-%d"))

    def pick_end_date(self):
        date = Querybox.get_date(parent=self.date_range_frame, title="选择结束日期")
        if date:
            self.date_end_entry.delete(0, tk.END)
            self.date_end_entry.insert(0, date.strftime("%Y-%m-%d"))

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f)
                
            # Basic
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
            
            # Behavior
            behavior = conf.get('behavior', {})
            self.min_delay.insert(0, behavior.get('min_delay', 5))
            self.max_delay.insert(0, behavior.get('max_delay', 15))
            self.timeout_entry.insert(0, behavior.get('timeout', 30000))
            self.headless_var.set(behavior.get('headless', False))
            
            # Browser
            browser = conf.get('browser', {})
            self.browser_path_var.set(browser.get('path', ''))
            self.browser_port_var.set(browser.get('port', 0))
            
            # Filters
            filters = search.get('filter', {})
            sort_val = filters.get('sort', 'totalrank')
            if sort_val in self.sort_map_rev:
                self.sort_cb.set(self.sort_map_rev[sort_val])
                
            dur_val = filters.get('duration', 0)
            if dur_val in self.dur_map_rev:
                self.dur_cb.set(self.dur_map_rev[dur_val])
                
            # Strategy
            strategy = search.get('strategy', {})
            strat_val = strategy.get('selection', 'order')
            if strat_val in self.strat_map_rev:
                self.strat_cb.set(self.strat_map_rev[strat_val])
            
            self.strict_match_var.set(strategy.get('strict_title_match', False))
            
            # Time Filter
            time_filter = filters.get('time_range', {})
            t_type = time_filter.get('type', 'none')
            t_map = {"none": "不限制", "recent": "近几天", "range": "指定日期范围"}
            if t_type in t_map:
                self.time_filter_cb.set(t_map[t_type])
                
            if t_type == "recent":
                self.recent_days_entry.delete(0, tk.END)
                self.recent_days_entry.insert(0, str(time_filter.get('value', 1)))
            elif t_type == "range":
                val = time_filter.get('value', {})
                if val.get('start'): self.date_start_entry.delete(0, tk.END); self.date_start_entry.insert(0, val['start'])
                if val.get('end'): self.date_end_entry.delete(0, tk.END); self.date_end_entry.insert(0, val['end'])
            
            self.on_time_filter_change() # Update UI visibility

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
            
            # Time Filter Logic
            t_selection = self.time_filter_cb.get()
            time_filter = {"type": "none", "value": None}
            if t_selection == "近几天":
                try:
                    days = int(self.recent_days_entry.get())
                    time_filter = {"type": "recent", "value": days}
                except:
                    messagebox.showerror("错误", "请输入有效的天数")
                    return False
            elif t_selection == "指定日期范围":
                start = self.date_start_entry.get()
                end = self.date_end_entry.get()
                if not start or not end:
                    messagebox.showerror("错误", "请输入日期范围")
                    return False
                time_filter = {"type": "range", "value": {"start": start, "end": end}}

            conf = {
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
            }
            
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
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
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
        
        # Helper to convert to int if possible for numeric sort
        def try_int(val):
            try: return int(val.replace("万", "0000").replace("+", "")) # Basic cleaning
            except: return val
            
        try:
            l.sort(key=lambda t: try_int(t[0]), reverse=reverse)
        except:
            l.sort(reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            self.tree.move(k, '', index)

        # Reverse sort next time
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
            self.root.clipboard_clear()
            self.root.clipboard_append(val)

    def copy_title(self):
        item = self.tree.selection()
        if item:
            val = self.tree.item(item[0])['values'][1]
            self.root.clipboard_clear()
            self.root.clipboard_append(val)

    def update_video_list(self, video_info):
        """Callback to update video list in GUI thread"""
        def _update():
            # Check if BV already exists
            found = False
            for item in self.tree.get_children():
                if self.tree.item(item)['values'][0] == video_info.get('bv'):
                    found = True
                    break
            
            if not found:
                # Add tag for striped rows
                tags = ('even',) if len(self.tree.get_children()) % 2 == 0 else ('odd',)
                self.tree.insert("", "end", values=(
                    video_info.get('bv', ''),
                    video_info.get('title', 'Unknown'),
                    video_info.get('author', 'Unknown'),
                    video_info.get('date', ''),
                    video_info.get('views', ''),
                    "Pending"
                ), tags=tags)
        
        # Configure tags for striped rows (if supported by theme, otherwise subtle difference)
        self.tree.tag_configure('odd', background='#F0F0F0')
        self.tree.tag_configure('even', background='#FFFFFF')
        
        self.root.after(0, _update)

    def update_video_status(self, bvid, status):
        """Update the status of a video in the list"""
        def _update():
            for item in self.tree.get_children():
                if self.tree.item(item)['values'][0] == bvid:
                    # Get current values
                    vals = list(self.tree.item(item)['values'])
                    vals[5] = status # Update status column
                    self.tree.item(item, values=vals)
                    break
        self.root.after(0, _update)

    def _run_backend(self):
        try:
            # Pass the callbacks
            backend_main.main(
                video_callback=self.update_video_list,
                status_callback=self.update_video_status
            )
            self.root.after(0, lambda: self.progress_var.set("任务完成"))

        except Exception as e:
            logger.error(f"任务异常: {e}")
            self.root.after(0, lambda: self.progress_var.set("任务异常"))
        finally:
            self.running = False
            self.root.after(0, lambda: self.start_btn.config(state="normal"))
            self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
            logger.info("任务结束。")

    def check_login_status(self):
        threading.Thread(target=self._check_login_thread, daemon=True).start()

    def _check_login_thread(self):
        self.root.after(0, lambda: self.status_label.config(text="检测中...", bootstyle="secondary"))
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context()
                auth = AuthManager(context, "cookies.json")
                if os.path.exists("cookies.json"):
                    with open("cookies.json", 'r', encoding='utf-8') as f:
                        context.add_cookies(json.load(f))
                is_logged_in = auth._check_login_status()
                browser.close()
                
                if is_logged_in:
                    self.root.after(0, lambda: self.status_label.config(text="已登录", bootstyle="success"))
                    logger.info("已登录")
                else:
                    self.root.after(0, lambda: self.status_label.config(text="未登录", bootstyle="danger"))
                    logger.warning("未登录")
        except Exception as e:
            logger.error(f"检测失败: {e}")
            self.root.after(0, lambda: self.status_label.config(text="出错", bootstyle="danger"))

    def qr_login(self):
        threading.Thread(target=self._qr_login_thread, daemon=True).start()

    def _qr_login_thread(self):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                auth = AuthManager(context, "cookies.json")
                if auth._qr_login():
                    self.root.after(0, lambda: self.status_label.config(text="已登录", bootstyle="success"))
                    messagebox.showinfo("成功", "登录成功")
                else:
                    messagebox.showwarning("失败", "登录失败")
                browser.close()
        except Exception as e:
            logger.error(f"登录出错: {e}")

if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    gui = BiliBotGUI(app)
    app.mainloop()
