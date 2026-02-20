import sys
import os
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from loguru import logger
import tkinter as tk

# Import tabs
from gui_tabs.comment_tab import CommentTab
from gui_tabs.warmup_tab import WarmupTab
from gui_tabs.ai_tab import AITab

# Redirect logs to GUI (throttled to reduce UI lag)
class TextHandler:
    _MAX_LINES = 1500
    _TRIM_LINES = 500
    _THROTTLE_MS = 100

    def __init__(self, text_widgets, root):
        self.text_widgets = text_widgets if isinstance(text_widgets, list) else [text_widgets]
        self.root = root
        self._queue = []
        self._after_id = None

    def write(self, string):
        if not string:
            return
        self._queue.append(string)
        if self._after_id is None:
            self._after_id = self.root.after(self._THROTTLE_MS, self._flush_log)

    def _flush_log(self):
        self._after_id = None
        if not self._queue:
            return
        text = "".join(self._queue)
        self._queue.clear()
        self.root.after(0, self._append_text, text)

    def _append_text(self, text):
        for widget in self.text_widgets:
            try:
                widget.insert(tk.END, text)
                widget.see(tk.END)
                line_count = int(widget.index("end-1c").split(".")[0])
                if line_count > self._MAX_LINES:
                    widget.delete("1.0", f"{self._TRIM_LINES}.0")
            except Exception:
                pass

    def flush(self):
        pass

class BiliBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bilibili 自动评论助手 V1.1")
        self.center_window(1280, 820)
        self.config_file = "config.yaml"

        self.setup_ui()
        
        # Log redirection to both tabs
        logger.remove()
        logger.add(
            TextHandler([self.comment_tab.log_area, self.warmup_tab.log_area], self.root), 
            format="{time:HH:mm:ss} | {message}"
        )
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        # Create Notebook for Tabs
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=8, pady=8)
        
        # 1. Auto Comment Tab
        self.comment_tab = CommentTab(self.notebook, self.config_file)
        self.notebook.add(self.comment_tab, text=" 自动评论模式 ")
        
        # 2. Warmup Mode Tab
        self.warmup_tab = WarmupTab(self.notebook, self.config_file)
        self.notebook.add(self.warmup_tab, text=" 养号模式 ")
        
        # 3. AI Settings Tab
        self.ai_tab = AITab(self.notebook, self.config_file)
        self.notebook.add(self.ai_tab, text=" AI 设置 ")
        
        # Bind tab change to handle task mutual exclusion if needed
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        # Optional: Check if a task is running in the other tab and warn user
        pass

    def on_closing(self):
        if hasattr(self.comment_tab, 'running') and self.comment_tab.running:
            self.comment_tab.stop_task()
        if hasattr(self.warmup_tab, 'running') and self.warmup_tab.running:
            self.warmup_tab.stop_task()
        self.root.destroy()

if __name__ == "__main__":
    try:
        app = ttk.Window(themename="cosmo", size=(1280, 820))
        gui = BiliBotGUI(app)
        app.mainloop()
    except Exception as e:
        print(f"GUI启动失败: {e}")
        import traceback
        traceback.print_exc()
