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
        self.root.geometry("600x900")
        self.config_file = "config.yaml"
        self.running = False
        
        # UI Setup
        self.setup_ui()
        self.load_config()
        
        # Log redirection
        logger.remove()
        logger.add(TextHandler(self.log_area), format="{time:HH:mm:ss} | {message}")

    def setup_ui(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=BOTH, expand=YES)
        
        # --- Section 1: Basic Config ---
        basic_group = ttk.Labelframe(main_frame, text="基础配置", padding=5)
        basic_group.pack(fill=X, pady=2)
        
        # Keywords
        ttk.Label(basic_group, text="搜索关键词 (逗号分隔):").pack(anchor=W)
        self.keywords_entry = ttk.Entry(basic_group)
        self.keywords_entry.pack(fill=X, pady=2)
        
        # Comment Text
        ttk.Label(basic_group, text="评论内容 (固定单条):").pack(anchor=W)
        self.comment_text = ttk.Text(basic_group, height=3)
        self.comment_text.pack(fill=X, pady=2)
        
        # Image Upload
        img_frame = ttk.Frame(basic_group)
        img_frame.pack(fill=X, pady=2)
        ttk.Label(img_frame, text="图片路径:").pack(side=LEFT)
        self.img_path_var = tk.StringVar()
        self.img_entry = ttk.Entry(img_frame, textvariable=self.img_path_var)
        self.img_entry.pack(side=LEFT, fill=X, expand=YES, padx=5)
        ttk.Button(img_frame, text="选择图片", command=self.select_image, bootstyle="info-outline").pack(side=RIGHT)

        # --- Section 2: Parameters ---
        param_group = ttk.Labelframe(main_frame, text="运行参数", padding=5)
        param_group.pack(fill=X, pady=2)
        
        # Row 1: Delay and Timeout
        r1 = ttk.Frame(param_group)
        r1.pack(fill=X, pady=2)
        ttk.Label(r1, text="操作间隔(秒):").pack(side=LEFT)
        self.min_delay = ttk.Entry(r1, width=5)
        self.min_delay.pack(side=LEFT, padx=5)
        ttk.Label(r1, text="-").pack(side=LEFT)
        self.max_delay = ttk.Entry(r1, width=5)
        self.max_delay.pack(side=LEFT, padx=5)
        
        ttk.Label(r1, text="超时(ms):").pack(side=LEFT, padx=(20, 5))
        self.timeout_entry = ttk.Entry(r1, width=8)
        self.timeout_entry.pack(side=LEFT)

        # Row 2: Max Videos and Headless
        r2 = ttk.Frame(param_group)
        r2.pack(fill=X, pady=2)
        ttk.Label(r2, text="最大评论数:").pack(side=LEFT)
        self.max_videos = ttk.Entry(r2, width=8)
        self.max_videos.pack(side=LEFT, padx=5)
        
        self.headless_var = tk.BooleanVar()
        ttk.Checkbutton(r2, text="显示浏览器窗口 (真实模式)", variable=self.headless_var, onvalue=False, offvalue=True).pack(side=LEFT, padx=20)

        # --- Section 2.5: Search Filters & Strategy ---
        filter_group = ttk.Labelframe(main_frame, text="搜索筛选与策略", padding=5)
        filter_group.pack(fill=X, pady=2)
        
        # Row 1: Sort and Duration
        fr1 = ttk.Frame(filter_group)
        fr1.pack(fill=X, pady=2)
        
        # Sort Order
        ttk.Label(fr1, text="排序方式:").pack(side=LEFT)
        self.sort_var = tk.StringVar(value="totalrank")
        sort_opts = [("综合排序", "totalrank"), ("最新发布", "pubdate"), ("最多播放", "click"), ("最多弹幕", "dm"), ("最多收藏", "stow")]
        self.sort_cb = ttk.Combobox(fr1, textvariable=self.sort_var, values=[x[0] for x in sort_opts], state="readonly", width=10)
        self.sort_cb.pack(side=LEFT, padx=5)
        self.sort_map = dict(sort_opts)
        self.sort_map_rev = {v: k for k, v in sort_opts}
        self.sort_cb.current(0)
        self.sort_cb.bind("<<ComboboxSelected>>", lambda e: self.sort_var.set(self.sort_map[self.sort_cb.get()]))

        # Duration
        ttk.Label(fr1, text="时长筛选:").pack(side=LEFT, padx=(15, 0))
        self.duration_var = tk.IntVar(value=0)
        dur_opts = [("全部时长", 0), ("10分钟以下", 1), ("10-30分钟", 2), ("30-60分钟", 3), ("60分钟以上", 4)]
        self.dur_cb = ttk.Combobox(fr1, values=[x[0] for x in dur_opts], state="readonly", width=10)
        self.dur_cb.pack(side=LEFT, padx=5)
        self.dur_map = dict(dur_opts)
        self.dur_map_rev = {v: k for k, v in dur_opts}
        self.dur_cb.current(0)
        
        # Row 2: Strategy
        fr2 = ttk.Frame(filter_group)
        fr2.pack(fill=X, pady=2)
        
        ttk.Label(fr2, text="选择策略:").pack(side=LEFT)
        self.strategy_var = tk.StringVar(value="order")
        strat_opts = [("顺序选择", "order"), ("随机选择", "random")]
        self.strat_cb = ttk.Combobox(fr2, values=[x[0] for x in strat_opts], state="readonly", width=10)
        self.strat_cb.pack(side=LEFT, padx=5)
        self.strat_map = dict(strat_opts)
        self.strat_map_rev = {v: k for k, v in strat_opts}
        self.strat_cb.current(0)

        # --- Section 3: Account ---
        auth_group = ttk.Labelframe(main_frame, text="账号状态", padding=5)
        auth_group.pack(fill=X, pady=2)
        
        self.status_label = ttk.Label(auth_group, text="未检测", bootstyle="secondary")
        self.status_label.pack(side=LEFT, padx=10)
        
        ttk.Button(auth_group, text="检测登录态", command=self.check_login_status, bootstyle="warning-outline").pack(side=LEFT, padx=5)
        ttk.Button(auth_group, text="扫码登录", command=self.qr_login, bootstyle="primary").pack(side=LEFT, padx=5)

        # --- Section 4: Control & Logs ---
        ctrl_frame = ttk.Frame(main_frame)
        ctrl_frame.pack(fill=X, pady=5)
        
        self.start_btn = ttk.Button(ctrl_frame, text="保存配置并开始任务", command=self.start_task, bootstyle="success")
        self.start_btn.pack(fill=X, pady=2)
        
        self.stop_btn = ttk.Button(ctrl_frame, text="停止任务", command=self.stop_task, bootstyle="danger", state="disabled")
        self.stop_btn.pack(fill=X, pady=2)
        
        self.progress_var = tk.StringVar(value="就绪")
        self.progress_label = ttk.Label(ctrl_frame, textvariable=self.progress_var, bootstyle="info")
        self.progress_label.pack(fill=X, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(main_frame, height=20, state='normal')
        self.log_area.pack(fill=BOTH, expand=YES, pady=5)

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f)
                
            # Populate fields
            keywords = ",".join(conf.get('search', {}).get('keywords', []))
            self.keywords_entry.insert(0, keywords)
            
            comments = conf.get('comment', {}).get('texts', [])
            if comments:
                self.comment_text.insert("1.0", comments[0])
                
            images = conf.get('comment', {}).get('images', [])
            if images:
                self.img_path_var.set(images[0])
                
            behavior = conf.get('behavior', {})
            self.min_delay.insert(0, behavior.get('min_delay', 5))
            self.max_delay.insert(0, behavior.get('max_delay', 15))
            self.timeout_entry.insert(0, behavior.get('timeout', 30000))
            self.headless_var.set(behavior.get('headless', False))
            
            search = conf.get('search', {})
            self.max_videos.insert(0, search.get('max_videos_per_keyword', 5))
            
            # Filters
            filters = search.get('filter', {})
            sort_val = filters.get('sort', 'totalrank')
            if sort_val in self.sort_map_rev:
                self.sort_cb.set(self.sort_map_rev[sort_val])
                self.sort_var.set(sort_val)
                
            dur_val = filters.get('duration', 0)
            if dur_val in self.dur_map_rev:
                self.dur_cb.set(self.dur_map_rev[dur_val])
                
            # Strategy
            strategy = search.get('strategy', {})
            strat_val = strategy.get('selection', 'order')
            if strat_val in self.strat_map_rev:
                self.strat_cb.set(self.strat_map_rev[strat_val])
                self.strategy_var.set(strat_val)
            
        except Exception as e:
            messagebox.showerror("错误", f"读取配置失败: {e}")

    def save_config(self):
        try:
            keywords = [k.strip() for k in self.keywords_entry.get().split(",") if k.strip()]
            if not keywords:
                messagebox.showerror("错误", "请至少输入一个搜索关键词！")
                return False
            
            comment = self.comment_text.get("1.0", tk.END).strip()
            if not comment:
                messagebox.showerror("错误", "请输入评论内容！")
                return False
            
            try:
                min_delay_val = float(self.min_delay.get())
                max_delay_val = float(self.max_delay.get())
                if min_delay_val < 0 or max_delay_val < min_delay_val:
                    messagebox.showerror("错误", "延迟时间设置不合法！")
                    return False
            except ValueError:
                messagebox.showerror("错误", "延迟时间必须是数字！")
                return False
            
            try:
                max_videos_val = int(self.max_videos.get())
                if max_videos_val < 1:
                    messagebox.showerror("错误", "最大评论数必须大于0！")
                    return False
            except ValueError:
                messagebox.showerror("错误", "最大评论数必须是整数！")
                return False
            
            try:
                timeout_val = int(self.timeout_entry.get())
                if timeout_val < 1000:
                    messagebox.showerror("错误", "超时时间不能小于1000ms！")
                    return False
            except ValueError:
                messagebox.showerror("错误", "超时时间必须是整数！")
                return False
            
            img_path = self.img_path_var.get().strip()
            
            if img_path:
                if not os.path.exists(img_path):
                    messagebox.showwarning("警告", f"图片文件不存在: {img_path}")
                img_path = img_path.replace("\\", "/")
            
            # Get values from combobox maps
            sort_val = self.sort_map.get(self.sort_cb.get(), "totalrank")
            dur_val = self.dur_map.get(self.dur_cb.get(), 0)
            strat_val = self.strat_map.get(self.strat_cb.get(), "order")

            conf = {
                "account": {"cookie_file": "cookies.json"},
                "search": {
                    "keywords": keywords,
                    "max_videos_per_keyword": int(self.max_videos.get()),
                    "filter": {
                        "sort": sort_val,
                        "duration": dur_val
                    },
                    "strategy": {
                        "selection": strat_val,
                        "random_pool_size": 20 # Fixed for now
                    }
                },
                "comment": {
                    "texts": [comment] if comment else [],
                    "images": [img_path] if img_path else []
                },
                "behavior": {
                    "min_delay": float(self.min_delay.get()),
                    "max_delay": float(self.max_delay.get()),
                    "headless": self.headless_var.get(),
                    "timeout": int(self.timeout_entry.get())
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(conf, f, allow_unicode=True, sort_keys=False)
            
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败: {e}")
            return False

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg *.gif")])
        if path:
            self.img_path_var.set(path)

    def start_task(self):
        if not self.save_config():
            return
            
        if self.running:
            return
            
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
            logger.info("正在停止任务...")
            self.progress_var.set("正在停止...")
            backend_main.stop_task()
            self.stop_btn.config(state="disabled")

    def _run_backend(self):
        try:
            backend_main.main()
            self.progress_var.set("任务完成")
        except Exception as e:
            logger.error(f"任务异常: {e}")
            self.progress_var.set("任务异常")
        finally:
            self.running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            logger.info("任务结束。")

    def check_login_status(self):
        def _check():
            self.status_label.config(text="检测中...", bootstyle="secondary")
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True) # Check silently
                    context = browser.new_context()
                    auth = AuthManager(context, "cookies.json")
                    # We need to manually load cookies here since AuthManager.login usually does it
                    # But login() also triggers QR if failed. We just want check.
                    
                    if os.path.exists("cookies.json"):
                        with open("cookies.json", 'r', encoding='utf-8') as f:
                            context.add_cookies(json.load(f)) # json is valid yaml
                    
                    is_logged_in = auth._check_login_status()
                    browser.close()
                    
                    if is_logged_in:
                        self.status_label.config(text="已登录", bootstyle="success")
                        logger.info("账号状态: 已登录")
                    else:
                        self.status_label.config(text="未登录", bootstyle="danger")
                        logger.warning("账号状态: 未登录")
            except Exception as e:
                logger.error(f"检测失败: {e}")
                self.status_label.config(text="检测出错", bootstyle="danger")

        threading.Thread(target=_check, daemon=True).start()

    def qr_login(self):
        def _login():
            try:
                with sync_playwright() as p:
                    # Must be headless=False to scan QR
                    browser = p.chromium.launch(headless=False)
                    context = browser.new_context()
                    auth = AuthManager(context, "cookies.json")
                    if auth._qr_login():
                        self.status_label.config(text="已登录", bootstyle="success")
                        messagebox.showinfo("成功", "登录成功！")
                    else:
                        messagebox.showwarning("失败", "登录失败或超时")
                    browser.close()
            except Exception as e:
                logger.error(f"登录过程出错: {e}")

        threading.Thread(target=_login, daemon=True).start()

if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    gui = BiliBotGUI(app)
    app.mainloop()
