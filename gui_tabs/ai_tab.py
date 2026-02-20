import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import threading
import yaml
import os
from loguru import logger


class AITab(ttk.Frame):
    def __init__(self, master, config_file, **kwargs):
        super().__init__(master, **kwargs)
        self.config_file = config_file

        self.ai_enabled_var = tk.BooleanVar(value=False)
        self.base_url_var = tk.StringVar(value="https://api.deepseek.com/v1")
        self.api_key_var = tk.StringVar()
        self.model_var = tk.StringVar(value="deepseek-chat")
        self.timeout_var = tk.IntVar(value=30)
        self.max_retries_var = tk.IntVar(value=2)

        self.comment_enabled_var = tk.BooleanVar(value=True)
        self.style_var = tk.StringVar(value="casual")
        self.max_length_var = tk.IntVar(value=100)

        self.filter_enabled_var = tk.BooleanVar(value=True)

        self.setup_ui()
        self.load_config()

    def setup_ui(self):
        container = ttk.Frame(self)
        container.pack(fill=BOTH, expand=YES, padx=16, pady=12)

        api_group = ttk.Labelframe(container, text="API 连接", padding=12)
        api_group.pack(fill=X, pady=8)
        api_group.columnconfigure(1, weight=1)

        ttk.Checkbutton(api_group, text="启用 AI 功能", variable=self.ai_enabled_var, bootstyle="round-toggle").grid(row=0, column=0, columnspan=2, sticky=W, pady=4)

        ttk.Label(api_group, text="Base URL:").grid(row=1, column=0, sticky=W, pady=3)
        ttk.Entry(api_group, textvariable=self.base_url_var).grid(row=1, column=1, sticky=EW, padx=5, pady=3)

        ttk.Label(api_group, text="API Key:").grid(row=2, column=0, sticky=W, pady=3)
        self.api_key_entry = ttk.Entry(api_group, textvariable=self.api_key_var, show="●")
        self.api_key_entry.grid(row=2, column=1, sticky=EW, padx=5, pady=3)

        ttk.Label(api_group, text="模型名称:").grid(row=3, column=0, sticky=W, pady=3)
        ttk.Entry(api_group, textvariable=self.model_var).grid(row=3, column=1, sticky=EW, padx=5, pady=3)

        param_frame = ttk.Frame(api_group)
        param_frame.grid(row=4, column=0, columnspan=2, sticky=EW, pady=4)
        ttk.Label(param_frame, text="超时(s):").pack(side=LEFT)
        ttk.Entry(param_frame, textvariable=self.timeout_var, width=6).pack(side=LEFT, padx=(2, 12))
        ttk.Label(param_frame, text="重试次数:").pack(side=LEFT)
        ttk.Entry(param_frame, textvariable=self.max_retries_var, width=4).pack(side=LEFT, padx=2)

        test_frame = ttk.Frame(api_group)
        test_frame.grid(row=5, column=0, columnspan=2, sticky=W, pady=6)
        ttk.Button(test_frame, text="测试连接", command=self._test_connection, bootstyle="info-outline", width=10).pack(side=LEFT)
        self.test_status = ttk.Label(test_frame, text="", bootstyle="secondary")
        self.test_status.pack(side=LEFT, padx=10)

        comment_group = ttk.Labelframe(container, text="智能评论", padding=12)
        comment_group.pack(fill=X, pady=8)
        comment_group.columnconfigure(1, weight=1)

        ttk.Checkbutton(comment_group, text="启用智能评论", variable=self.comment_enabled_var, bootstyle="round-toggle").grid(row=0, column=0, columnspan=2, sticky=W, pady=4)

        ttk.Label(comment_group, text="推广意图/人设:").grid(row=1, column=0, sticky=NW, pady=3)
        self.intent_text = tk.Text(comment_group, height=3, width=40)
        self.intent_text.grid(row=1, column=1, sticky=EW, padx=5, pady=3)

        style_frame = ttk.Frame(comment_group)
        style_frame.grid(row=2, column=0, columnspan=2, sticky=EW, pady=4)
        ttk.Label(style_frame, text="评论风格:").pack(side=LEFT)
        self.style_map = {"随意": "casual", "热情": "enthusiastic", "专业": "professional"}
        self.style_map_rev = {v: k for k, v in self.style_map.items()}
        self.style_cb = ttk.Combobox(style_frame, values=list(self.style_map.keys()), state="readonly", width=10)
        self.style_cb.pack(side=LEFT, padx=(2, 16))
        self.style_cb.current(0)
        ttk.Label(style_frame, text="最大字数:").pack(side=LEFT)
        ttk.Entry(style_frame, textvariable=self.max_length_var, width=6).pack(side=LEFT, padx=2)

        filter_group = ttk.Labelframe(container, text="智能筛选", padding=12)
        filter_group.pack(fill=X, pady=8)
        filter_group.columnconfigure(1, weight=1)

        ttk.Checkbutton(filter_group, text="启用智能筛选", variable=self.filter_enabled_var, bootstyle="round-toggle").grid(row=0, column=0, columnspan=2, sticky=W, pady=4)

        ttk.Label(filter_group, text="筛选标准:").grid(row=1, column=0, sticky=NW, pady=3)
        self.criteria_text = tk.Text(filter_group, height=3, width=40)
        self.criteria_text.grid(row=1, column=1, sticky=EW, padx=5, pady=3)

        btn_frame = ttk.Frame(container)
        btn_frame.pack(fill=X, pady=12)
        ttk.Button(btn_frame, text="保存配置", command=self.save_config, bootstyle="success", width=14).pack(side=LEFT)

    def load_config(self):
        if not os.path.exists(self.config_file):
            return
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                conf = yaml.safe_load(f) or {}
            ai = conf.get('ai', {})
            self.ai_enabled_var.set(ai.get('enabled', False))
            self.base_url_var.set(ai.get('base_url', 'https://api.deepseek.com/v1'))
            self.api_key_var.set(ai.get('api_key', ''))
            self.model_var.set(ai.get('model', 'deepseek-chat'))
            self.timeout_var.set(ai.get('timeout', 30))
            self.max_retries_var.set(ai.get('max_retries', 2))

            comment = ai.get('comment', {})
            self.comment_enabled_var.set(comment.get('enabled', True))
            intent = comment.get('user_intent', '')
            if intent:
                self.intent_text.insert("1.0", intent)
            style_val = comment.get('style', 'casual')
            if style_val in self.style_map_rev:
                self.style_cb.set(self.style_map_rev[style_val])
            self.max_length_var.set(comment.get('max_length', 100))

            filt = ai.get('filter', {})
            self.filter_enabled_var.set(filt.get('enabled', True))
            criteria = filt.get('criteria', '')
            if criteria:
                self.criteria_text.insert("1.0", criteria)
        except Exception as e:
            logger.error(f"AI Config Load Error: {e}")

    def save_config(self):
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    conf = yaml.safe_load(f) or {}
            else:
                conf = {}

            conf['ai'] = {
                'enabled': self.ai_enabled_var.get(),
                'base_url': self.base_url_var.get().strip(),
                'api_key': self.api_key_var.get().strip(),
                'model': self.model_var.get().strip(),
                'timeout': self.timeout_var.get(),
                'max_retries': self.max_retries_var.get(),
                'comment': {
                    'enabled': self.comment_enabled_var.get(),
                    'user_intent': self.intent_text.get("1.0", tk.END).strip(),
                    'style': self.style_map.get(self.style_cb.get(), 'casual'),
                    'max_length': self.max_length_var.get(),
                },
                'filter': {
                    'enabled': self.filter_enabled_var.get(),
                    'criteria': self.criteria_text.get("1.0", tk.END).strip(),
                },
            }

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(conf, f, allow_unicode=True, sort_keys=False)
            logger.info("AI 配置已保存")
            return True
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            return False

    def _test_connection(self):
        self.test_status.config(text="测试中...", bootstyle="secondary")
        threading.Thread(target=self._test_thread, daemon=True).start()

    def _test_thread(self):
        try:
            from openai import OpenAI
            client = OpenAI(
                base_url=self.base_url_var.get().strip(),
                api_key=self.api_key_var.get().strip(),
                timeout=10,
            )
            resp = client.chat.completions.create(
                model=self.model_var.get().strip(),
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=5,
            )
            if resp.choices:
                self.after(0, lambda: self.test_status.config(text="✅ 连接成功", bootstyle="success"))
            else:
                self.after(0, lambda: self.test_status.config(text="⚠️ 无响应", bootstyle="warning"))
        except Exception as e:
            self.after(0, lambda: self.test_status.config(text=f"❌ {e}", bootstyle="danger"))
