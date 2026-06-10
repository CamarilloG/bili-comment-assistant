import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
import threading
import yaml
import os
from loguru import logger
import main as backend_main

class WarmupTab(ttk.Frame):
    def __init__(self, master, config_file, **kwargs):
        super().__init__(master, **kwargs)
        self.config_file = config_file
        self.running = False
        
        # Variables
        self.duration_var = tk.IntVar(value=30)
        self.max_videos_var = tk.IntVar(value=20)
        self.watch_min_var = tk.IntVar(value=20)
        self.watch_max_var = tk.IntVar(value=240)
        
        self.random_pause_var = tk.BooleanVar(value=True)
        self.pause_prob_var = tk.DoubleVar(value=0.08)
        self.random_scroll_var = tk.BooleanVar(value=True)
        self.scroll_prob_var = tk.DoubleVar(value=0.10)
        self.view_comment_var = tk.BooleanVar(value=True)
        self.view_comment_prob_var = tk.DoubleVar(value=0.05)
        self.random_like_var = tk.BooleanVar(value=True)
        self.like_prob_var = tk.DoubleVar(value=0.30)
        
        self.enable_comment_var = tk.BooleanVar(value=False)
        self.comment_prob_var = tk.DoubleVar(value=0.1)
        self.comment_type_var = tk.StringVar(value="template")
        
        self.source_var = tk.StringVar(value="recommend")
        self.progress_var = tk.StringVar(value="就绪")
        
        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        # Main Paned Window
        self.paned = ttk.Panedwindow(self, orient=HORIZONTAL)
        self.paned.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        
        # --- LEFT PANEL: Configuration ---
        left_panel = ttk.Frame(self.paned)
        self.paned.add(left_panel, weight=2)

        # 1. Action bar (fixed at top)
        action_bar = ttk.Frame(left_panel)
        action_bar.pack(side=TOP, fill=X, pady=(0, 10))
        self.start_btn = ttk.Button(action_bar, text="启动养号", command=self.start_task, bootstyle="success", width=14)
        self.start_btn.pack(side=LEFT, padx=(0, 8))
        self.stop_btn = ttk.Button(action_bar, text="停止", command=self.stop_task, bootstyle="danger", state="disabled", width=10)
        self.stop_btn.pack(side=LEFT, padx=(0, 12))
        ttk.Label(action_bar, textvariable=self.progress_var, bootstyle="info", font=("", 10)).pack(side=LEFT)

        # 2. Scrollable Configuration Area
        config_scroll = ScrolledFrame(left_panel, autohide=True)
        config_scroll.pack(side=TOP, fill=BOTH, expand=YES)
        config_content = config_scroll

        # 1. Basic Control
        basic_group = ttk.Labelframe(config_content, text="基础控制", padding=12)
        basic_group.pack(fill=X, pady=8, padx=2)
        basic_group.columnconfigure(1, weight=1)
        ttk.Label(basic_group, text="单次养号时长 (分钟):").grid(row=0, column=0, sticky=W, pady=3)
        ttk.Entry(basic_group, textvariable=self.duration_var, width=10).grid(row=0, column=1, sticky=EW, padx=5, pady=3)
        ttk.Label(basic_group, text="最大刷视频数量:").grid(row=1, column=0, sticky=W, pady=3)
        ttk.Entry(basic_group, textvariable=self.max_videos_var, width=10).grid(row=1, column=1, sticky=EW, padx=5, pady=3)

        # 2. Playback Behavior
        behavior_group = ttk.Labelframe(config_content, text="播放行为设置", padding=12)
        behavior_group.pack(fill=X, pady=8, padx=2)
        
        behavior_group.columnconfigure(1, weight=1)
        
        ttk.Label(behavior_group, text="视频播放时长 (秒):").grid(row=0, column=0, sticky=W, pady=2)
        watch_time_frame = ttk.Frame(behavior_group)
        watch_time_frame.grid(row=0, column=1, columnspan=3, sticky=EW, padx=5, pady=2)
        
        ttk.Entry(watch_time_frame, textvariable=self.watch_min_var, width=6).pack(side=LEFT, fill=X, expand=YES)
        ttk.Label(watch_time_frame, text="-").pack(side=LEFT, padx=5)
        ttk.Entry(watch_time_frame, textvariable=self.watch_max_var, width=6).pack(side=LEFT, fill=X, expand=YES)
        
        # Helper to create behavior rows
        def add_behavior_row(row_idx, label, var_toggle, var_prob):
            ttk.Checkbutton(behavior_group, text=label, variable=var_toggle, bootstyle="round-toggle").grid(row=row_idx, column=0, sticky=W, pady=2)
            prob_frame = ttk.Frame(behavior_group)
            prob_frame.grid(row=row_idx, column=1, sticky=E, padx=5)
            ttk.Label(prob_frame, text="概率:").pack(side=LEFT)
            ttk.Entry(prob_frame, textvariable=var_prob, width=6).pack(side=LEFT, padx=5)

        add_behavior_row(1, "随机暂停播放", self.random_pause_var, self.pause_prob_var)
        add_behavior_row(2, "随机滚动页面", self.random_scroll_var, self.scroll_prob_var)
        add_behavior_row(3, "随机查看评论区", self.view_comment_var, self.view_comment_prob_var)
        add_behavior_row(4, "随机点赞视频", self.random_like_var, self.like_prob_var)

        # 3. Comment Behavior
        comment_group = ttk.Labelframe(config_content, text="评论行为 (低频)", padding=12)
        comment_group.pack(fill=X, pady=8, padx=2)
        
        comment_group.columnconfigure(1, weight=1)
        
        ttk.Checkbutton(comment_group, text="启用随机评论", variable=self.enable_comment_var, bootstyle="round-toggle").grid(row=0, column=0, sticky=W, pady=2)
        
        prob_frame = ttk.Frame(comment_group)
        prob_frame.grid(row=0, column=1, sticky=E, padx=5)
        ttk.Label(prob_frame, text="触发概率 (0~1):").pack(side=LEFT)
        ttk.Entry(prob_frame, textvariable=self.comment_prob_var, width=6).pack(side=LEFT, padx=5)
        
        ttk.Label(comment_group, text="评论生成方式:").grid(row=1, column=0, sticky=W, pady=(5, 2))
        ttk.Radiobutton(comment_group, text="模板评论", variable=self.comment_type_var, value="template").grid(row=2, column=0, sticky=W, padx=10)
        ttk.Radiobutton(comment_group, text="AI生成 (DeepSeek) - 暂未开放", variable=self.comment_type_var, value="ai", state=DISABLED).grid(row=3, column=0, columnspan=2, sticky=W, padx=10)

        # 4. Video Source
        source_group = ttk.Labelframe(config_content, text="视频来源", padding=12)
        source_group.pack(fill=X, pady=8, padx=2)
        ttk.Radiobutton(source_group, text="首页推荐", variable=self.source_var, value="recommend").pack(anchor=W, pady=2)
        ttk.Radiobutton(source_group, text="关键词搜索 (预留)", variable=self.source_var, value="search", state=DISABLED).pack(anchor=W, pady=2)

        # --- RIGHT PANEL: Status & Logs ---
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        status_group = ttk.Labelframe(right_frame, text="运行状态", padding=12)
        status_group.pack(fill=X, pady=8)
        self.current_video_label = ttk.Label(status_group, text="当前视频: 无", font=("", 10, "bold"))
        self.current_video_label.pack(anchor=W, pady=5)
        self.stats_label = ttk.Label(status_group, text="已观看: 0 | 累计时长: 0 min | 已点赞: 0 | 已评论: 0", bootstyle="secondary")
        self.stats_label.pack(anchor=W, pady=5)

        log_frame = ttk.Labelframe(right_frame, text="运行日志", padding=12)
        log_frame.pack(fill=BOTH, expand=YES, pady=8)
        self.log_area = scrolledtext.ScrolledText(log_frame, height=10, state='normal')
        self.log_area.pack(fill=BOTH, expand=YES)

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f) or {}
            
            warmup = conf.get('warmup', {})
            basic = warmup.get('basic', {})
            self.duration_var.set(basic.get('duration_minutes', 30))
            self.max_videos_var.set(basic.get('max_videos', 20))
            
            behavior = warmup.get('behavior', {})
            self.watch_min_var.set(behavior.get('watch_time_min', 20))
            self.watch_max_var.set(behavior.get('watch_time_max', 240))
            self.random_pause_var.set(behavior.get('random_pause', True))
            self.pause_prob_var.set(behavior.get('pause_prob', 0.08))
            self.random_scroll_var.set(behavior.get('random_scroll', True))
            self.scroll_prob_var.set(behavior.get('scroll_prob', 0.10))
            self.view_comment_var.set(behavior.get('view_comment', True))
            self.view_comment_prob_var.set(behavior.get('view_comment_prob', 0.05))
            self.random_like_var.set(behavior.get('random_like', True))
            self.like_prob_var.set(behavior.get('like_prob', 0.30))
            
            comment = warmup.get('comment', {})
            self.enable_comment_var.set(comment.get('enable', False))
            self.comment_prob_var.set(comment.get('probability', 0.1))
            self.comment_type_var.set(comment.get('type', 'template'))
            
            self.source_var.set(warmup.get('source', 'recommend'))
        except Exception as e:
            logger.error(f"Warmup Config Load Error: {e}")

    def save_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    conf = yaml.safe_load(f) or {}
            else:
                conf = {}

            conf['warmup'] = {
                'basic': {
                    'duration_minutes': self.duration_var.get(),
                    'max_videos': self.max_videos_var.get()
                },
                'behavior': {
                    'watch_time_min': self.watch_min_var.get(),
                    'watch_time_max': self.watch_max_var.get(),
                    'random_pause': self.random_pause_var.get(),
                    'pause_prob': self.pause_prob_var.get(),
                    'random_scroll': self.random_scroll_var.get(),
                    'scroll_prob': self.scroll_prob_var.get(),
                    'view_comment': self.view_comment_var.get(),
                    'view_comment_prob': self.view_comment_prob_var.get(),
                    'random_like': self.random_like_var.get(),
                    'like_prob': self.like_prob_var.get()
                },
                'comment': {
                    'enable': self.enable_comment_var.get(),
                    'probability': self.comment_prob_var.get(),
                    'type': self.comment_type_var.get()
                },
                'source': self.source_var.get()
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(conf, f, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            return False

    def start_task(self):
        if not self.save_config(): return
        if self.running: return
        
        self.running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set("养号中...")
        logger.info("养号模式已启动...")
        
        t = threading.Thread(target=self._run_backend)
        t.daemon = True
        t.start()

    def stop_task(self):
        if self.running:
            logger.info("正在停止养号...")
            self.progress_var.set("正在停止...")
            backend_main.stop_task()
            self.stop_btn.config(state="disabled")

    def update_status(self, video_title, watched_count, total_time, like_count, comment_count):
        def _update():
            self.current_video_label.config(text=f"当前视频: {video_title}")
            self.stats_label.config(text=f"已观看: {watched_count} | 累计时长: {total_time} min | 已点赞: {like_count} | 已评论: {comment_count}")
        self.after(0, _update)

    def _run_backend(self):
        try:
            backend_main.run_warmup(
                status_callback=self.update_status
            )
            self.after(0, lambda: self.progress_var.set("养号完成"))
        except Exception as e:
            logger.error(f"养号异常: {e}")
            self.after(0, lambda: self.progress_var.set("养号异常"))
        finally:
            self.running = False
            self.after(0, lambda: self.start_btn.config(state="normal"))
            self.after(0, lambda: self.stop_btn.config(state="disabled"))
            logger.info("养号结束。")
