import sys
import os
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from loguru import logger
import tkinter as tk

# Import tabs
from gui_tabs.comment_tab import CommentTab
from gui_tabs.warmup_tab import WarmupTab

# Redirect logs to GUI
class TextHandler:
    def __init__(self, text_widgets):
        self.text_widgets = text_widgets if isinstance(text_widgets, list) else [text_widgets]

    def write(self, string):
        for widget in self.text_widgets:
            try:
                widget.insert(tk.END, string)
                widget.see(tk.END)
            except:
                pass

    def flush(self):
        pass

class BiliBotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bilibili 自动评论助手 V1.1")
        self.root.geometry("1200x850")
        self.config_file = "config.yaml"
        
        self.setup_ui()
        
        # Log redirection to both tabs
        logger.remove()
        logger.add(
            TextHandler([self.comment_tab.log_area, self.warmup_tab.log_area]), 
            format="{time:HH:mm:ss} | {message}"
        )

    def setup_ui(self):
        # Create Notebook for Tabs
        self.notebook = ttk.Notebook(self.root, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        
        # 1. Auto Comment Tab
        self.comment_tab = CommentTab(self.notebook, self.config_file)
        self.notebook.add(self.comment_tab, text=" 自动评论模式 ")
        
        # 2. Warmup Mode Tab
        self.warmup_tab = WarmupTab(self.notebook, self.config_file)
        self.notebook.add(self.warmup_tab, text=" 养号模式 ")
        
        # Bind tab change to handle task mutual exclusion if needed
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        # Optional: Check if a task is running in the other tab and warn user
        pass

if __name__ == "__main__":
    app = ttk.Window(themename="flatly")
    gui = BiliBotGUI(app)
    app.mainloop()
