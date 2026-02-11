import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
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
        self.random_scroll_var = tk.BooleanVar(value=True)
        self.view_comment_var = tk.BooleanVar(value=True)
        
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
        left_frame = ttk.Frame(self.paned)
        self.paned.add(left_frame, weight=1)
        
        # 1. Basic Control
        basic_group = ttk.Labelframe(left_frame, text="基础控制", padding=5)
        basic_group.pack(fill=X, pady=2)
        
        r1 = ttk.Frame(basic_group)
        r1.pack(fill=X, pady=2)
        ttk.Label(r1, text="单次养号时长 (分钟):").pack(side=LEFT)
        ttk.Entry(r1, textvariable=self.duration_var, width=6).pack(side=LEFT, padx=5)
        
        r2 = ttk.Frame(basic_group)
        r2.pack(fill=X, pady=2)
        ttk.Label(r2, text="最大刷视频数量:").pack(side=LEFT)
        ttk.Entry(r2, textvariable=self.max_videos_var, width=6).pack(side=LEFT, padx=5)

        # 2. Playback Behavior
        behavior_group = ttk.Labelframe(left_frame, text="播放行为设置", padding=5)
        behavior_group.pack(fill=X, pady=2)
        
        r3 = ttk.Frame(behavior_group)
        r3.pack(fill=X, pady=2)
        ttk.Label(r3, text="视频播放时长 (秒):").pack(side=LEFT)
        ttk.Entry(r3, textvariable=self.watch_min_var, width=4).pack(side=LEFT, padx=2)
        ttk.Label(r3, text="-").pack(side=LEFT)
        ttk.Entry(r3, textvariable=self.watch_max_var, width=4).pack(side=LEFT, padx=2)
        
        ttk.Checkbutton(behavior_group, text="随机暂停播放", variable=self.random_pause_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        ttk.Checkbutton(behavior_group, text="随机滚动页面", variable=self.random_scroll_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        ttk.Checkbutton(behavior_group, text="随机查看评论区", variable=self.view_comment_var, bootstyle="round-toggle").pack(anchor=W, pady=2)

        # 3. Comment Behavior
        comment_group = ttk.Labelframe(left_frame, text="评论行为 (低频)", padding=5)
        comment_group.pack(fill=X, pady=2)
        
        ttk.Checkbutton(comment_group, text="启用随机评论", variable=self.enable_comment_var, bootstyle="round-toggle").pack(anchor=W, pady=2)
        
        r4 = ttk.Frame(comment_group)
        r4.pack(fill=X, pady=2)
        ttk.Label(r4, text="评论触发概率 (0~1):").pack(side=LEFT)
        ttk.Entry(r4, textvariable=self.comment_prob_var, width=6).pack(side=LEFT, padx=5)
        
        ttk.Label(comment_group, text="评论生成方式:").pack(anchor=W, pady=(5, 0))
        ttk.Radiobutton(comment_group, text="模板评论", variable=self.comment_type_var, value="template").pack(anchor=W)
        ttk.Radiobutton(comment_group, text="AI生成 (DeepSeek) - 暂未开放", variable=self.comment_type_var, value="ai", state=DISABLED).pack(anchor=W)

        # 4. Video Source
        source_group = ttk.Labelframe(left_frame, text="视频来源", padding=5)
        source_group.pack(fill=X, pady=2)
        ttk.Radiobutton(source_group, text="首页推荐", variable=self.source_var, value="recommend").pack(anchor=W)
        ttk.Radiobutton(source_group, text="关键词搜索 (预留)", variable=self.source_var, value="search", state=DISABLED).pack(anchor=W)

        # 5. Control
        ctrl_frame = ttk.Frame(left_frame)
        ctrl_frame.pack(fill=X, pady=10)
        self.start_btn = ttk.Button(ctrl_frame, text="启动养号", command=self.start_task, bootstyle="success")
        self.start_btn.pack(fill=X, pady=2)
        self.stop_btn = ttk.Button(ctrl_frame, text="停止", command=self.stop_task, bootstyle="danger", state="disabled")
        self.stop_btn.pack(fill=X, pady=2)
        ttk.Label(ctrl_frame, textvariable=self.progress_var, bootstyle="info").pack(fill=X, pady=5)

        # --- RIGHT PANEL: Status & Logs ---
        right_frame = ttk.Frame(self.paned)
        self.paned.add(right_frame, weight=3)
        
        status_group = ttk.Labelframe(right_frame, text="运行状态", padding=5)
        status_group.pack(fill=X, pady=2)
        
        self.current_video_label = ttk.Label(status_group, text="当前视频: 无", font=("", 10, "bold"))
        self.current_video_label.pack(anchor=W, pady=2)
        
        self.stats_label = ttk.Label(status_group, text="已观看: 0 | 累计时长: 0 min | 已评论: 0")
        self.stats_label.pack(anchor=W, pady=2)

        log_frame = ttk.Labelframe(right_frame, text="运行日志", padding=5)
        log_frame.pack(fill=BOTH, expand=YES, pady=2)
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
            self.random_scroll_var.set(behavior.get('random_scroll', True))
            self.view_comment_var.set(behavior.get('view_comment', True))
            
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
                    'random_scroll': self.random_scroll_var.get(),
                    'view_comment': self.view_comment_var.get()
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

    def update_status(self, video_title, watched_count, total_time, comment_count):
        def _update():
            self.current_video_label.config(text=f"当前视频: {video_title}")
            self.stats_label.config(text=f"已观看: {watched_count} | 累计时长: {total_time} min | 已评论: {comment_count}")
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
