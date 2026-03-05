# Excel式视频信息表格组件

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Optional


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
            self, columns=columns, show="headings", selectmode="browse", height=20
        )

        # 设置列标题和宽度
        column_widths = {
            "序号": 50,
            "标题": 350,
            "作者": 120,
            "链接": 150,
            "点赞数": 80,
            "评论数": 80,
            "状态": 100,
        }

        for col in columns:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(
                col,
                width=column_widths.get(col, 100),
                anchor="w" if col in ["标题", "作者", "链接"] else "center",
            )

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

        # 绑定双击事件
        self.tree.bind("<Double-1>", self._on_double_click)

    def _on_double_click(self, event):
        """双击行时的处理"""
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            values = self.tree.item(item, "values")
            if values and len(values) > 3:
                # 复制链接到剪贴板
                link = values[3]
                self.clipboard_clear()
                self.clipboard_append(link)
                print(f"[表格] 已复制链接: {link}")

    def add_video(self, video: Dict):
        """添加视频到表格"""
        self.videos.append(video)
        idx = len(self.videos)

        # 截断过长的文本
        title = video.get("title", "Unknown")
        if len(title) > 50:
            title = title[:47] + "..."

        url = video.get("url", "")
        if len(url) > 40:
            url = url[:37] + "..."

        values = (
            idx,
            title,
            video.get("author", "Unknown"),
            url,
            video.get("likes", "-"),
            video.get("comment_count", "-"),
            video.get("status", "待处理"),
        )

        # 插入行，使用tag标记索引
        item_id = self.tree.insert("", "end", values=values, tags=(f"video_{idx}",))

        # 滚动到最新添加的行
        self.tree.see(item_id)

    def update_video_status(self, index: int, status: str, **kwargs):
        """
        更新视频状态

        :param index: 视频索引（从0开始）
        :param status: 新状态
        :param kwargs: 其他要更新的字段
        """
        if 0 <= index < len(self.videos):
            # 更新数据
            self.videos[index]["status"] = status
            for key, value in kwargs.items():
                self.videos[index][key] = value

            # 更新表格显示
            children = self.tree.get_children()
            if index < len(children):
                item_id = children[index]
                video = self.videos[index]

                title = video.get("title", "Unknown")
                if len(title) > 50:
                    title = title[:47] + "..."

                url = video.get("url", "")
                if len(url) > 40:
                    url = url[:37] + "..."

                values = (
                    index + 1,
                    title,
                    video.get("author", "Unknown"),
                    url,
                    video.get("likes", "-"),
                    video.get("comment_count", "-"),
                    status,
                )
                self.tree.item(item_id, values=values)

                # 根据状态设置颜色
                if "成功" in status or "完成" in status:
                    self.tree.item(item_id, tags=(f"video_{index + 1}", "success"))
                elif "失败" in status or "错误" in status:
                    self.tree.item(item_id, tags=(f"video_{index + 1}", "error"))

        # 配置tag颜色
        self.tree.tag_configure("success", foreground="green")
        self.tree.tag_configure("error", foreground="red")

    def clear(self):
        """清空表格"""
        self.videos.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)

    def get_selected_video(self) -> Optional[tuple[int, Dict]]:
        """
        获取选中的视频

        :return: (索引, 视频信息) 或 None
        """
        selection = self.tree.selection()
        if not selection:
            return None

        item = selection[0]
        values = self.tree.item(item, "values")
        if values:
            idx = int(values[0]) - 1
            if 0 <= idx < len(self.videos):
                return idx, self.videos[idx]
        return None

    def get_all_videos(self) -> List[Dict]:
        """获取所有视频"""
        return self.videos.copy()

    def get_video_count(self) -> int:
        """获取视频总数"""
        return len(self.videos)
