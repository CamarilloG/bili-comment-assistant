"""
License 验证 GUI
使用 tkinter 创建简单的验证界面
"""
import os
import sys
from pathlib import Path
from typing import Optional, Callable

from license.validator import validate_license

# 尝试导入 tkinter
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
    print("[License] 警告: tkinter 不可用，将使用命令行模式")

# 尝试导入 tkinterdnd2（可选）
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    TKINTERDND_AVAILABLE = True
except ImportError:
    TKINTERDND_AVAILABLE = False


class LicenseVerificationGUI:
    """License 验证 GUI"""

    def __init__(self, on_success: Optional[Callable] = None):
        """
        初始化 GUI

        Args:
            on_success: 验证成功后的回调函数
        """
        self.on_success = on_success
        self.license_data = None
        self.root = None

    def create_window(self):
        """创建窗口"""
        if not TKINTER_AVAILABLE:
            raise ImportError("tkinter 不可用")

        # 使用 TkinterDnD 支持拖拽
        if TKINTERDND_AVAILABLE:
            try:
                self.root = TkinterDnD.Tk()
            except:
                self.root = tk.Tk()
        else:
            self.root = tk.Tk()

        self.root.title("B站评论助手 - License 验证")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # 居中显示
        self.center_window()

        # 创建界面元素
        self.create_widgets()

        # 尝试自动加载 license
        self.auto_load_license()

    def center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def create_widgets(self):
        """创建界面元素"""
        # 标题
        title_frame = tk.Frame(self.root, bg="#2563eb", height=80)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="B站评论助手",
            font=("Microsoft YaHei UI", 20, "bold"),
            bg="#2563eb",
            fg="white"
        )
        title_label.pack(pady=20)

        # 主内容区域
        content_frame = tk.Frame(self.root, padx=40, pady=30)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 说明文字
        info_label = tk.Label(
            content_frame,
            text="请选择或拖拽 License 文件进行验证",
            font=("Microsoft YaHei UI", 11),
            fg="#6b7280"
        )
        info_label.pack(pady=(0, 20))

        # 文件路径显示
        self.path_var = tk.StringVar(value="未选择文件")
        path_label = tk.Label(
            content_frame,
            textvariable=self.path_var,
            font=("Microsoft YaHei UI", 9),
            fg="#9ca3af",
            wraplength=400
        )
        path_label.pack(pady=(0, 20))

        # 按钮区域
        button_frame = tk.Frame(content_frame)
        button_frame.pack(pady=10)

        # 选择文件按钮
        select_btn = tk.Button(
            button_frame,
            text="选择 License 文件",
            command=self.select_file,
            font=("Microsoft YaHei UI", 10),
            bg="#3b82f6",
            fg="white",
            activebackground="#2563eb",
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2"
        )
        select_btn.pack(side=tk.LEFT, padx=5)

        # 验证按钮
        self.verify_btn = tk.Button(
            button_frame,
            text="验证 License",
            command=self.verify_license,
            font=("Microsoft YaHei UI", 10),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief=tk.FLAT,
            padx=20,
            pady=10,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.verify_btn.pack(side=tk.LEFT, padx=5)

        # 状态信息
        self.status_var = tk.StringVar(value="")
        self.status_label = tk.Label(
            content_frame,
            textvariable=self.status_var,
            font=("Microsoft YaHei UI", 9),
            wraplength=400,
            justify=tk.LEFT
        )
        self.status_label.pack(pady=(20, 0))

        # 拖拽区域（如果支持）
        if TKINTERDND_AVAILABLE and hasattr(self.root, 'drop_target_register'):
            drop_frame = tk.Frame(
                content_frame,
                bg="#f3f4f6",
                relief=tk.SOLID,
                borderwidth=2,
                height=80
            )
            drop_frame.pack(fill=tk.X, pady=(20, 0))
            drop_frame.pack_propagate(False)

            drop_label = tk.Label(
                drop_frame,
                text="或将 License 文件拖拽到此处",
                font=("Microsoft YaHei UI", 10),
                bg="#f3f4f6",
                fg="#9ca3af"
            )
            drop_label.pack(expand=True)

            # 注册拖拽事件
            drop_frame.drop_target_register(DND_FILES)
            drop_frame.dnd_bind('<<Drop>>', self.on_drop)

    def select_file(self):
        """选择文件"""
        file_path = filedialog.askopenfilename(
            title="选择 License 文件",
            filetypes=[
                ("License 文件", "*.lic"),
                ("所有文件", "*.*")
            ]
        )

        if file_path:
            self.set_license_path(file_path)

    def on_drop(self, event):
        """拖拽文件事件"""
        # 获取文件路径（可能包含花括号）
        file_path = event.data.strip('{}')
        self.set_license_path(file_path)

    def set_license_path(self, file_path: str):
        """设置 license 文件路径"""
        self.license_path = file_path
        self.path_var.set(f"已选择: {Path(file_path).name}")
        self.verify_btn.config(state=tk.NORMAL)
        self.status_var.set("")

    def auto_load_license(self):
        """自动加载 license 文件"""
        # 尝试从固定路径加载
        default_paths = [
            "./license.lic",
            "./License.lic",
            os.path.join(os.path.dirname(sys.executable), "license.lic"),
        ]

        for path in default_paths:
            if os.path.exists(path):
                self.set_license_path(path)
                # 自动验证
                self.root.after(500, self.verify_license)
                break

    def verify_license(self):
        """验证 license"""
        if not hasattr(self, 'license_path'):
            self.status_var.set("❌ 请先选择 License 文件")
            self.status_label.config(fg="#ef4444")
            return

        # 显示验证中
        self.status_var.set("⏳ 正在验证...")
        self.status_label.config(fg="#3b82f6")
        self.verify_btn.config(state=tk.DISABLED)
        self.root.update()

        # 执行验证
        valid, message, data = validate_license(self.license_path)

        if valid:
            self.license_data = data
            self.status_var.set(f"✅ 验证成功！\n\n用户: {data.get('user', 'N/A')}\n授权类型: {data.get('type', '标准版')}")
            self.status_label.config(fg="#10b981")

            # 延迟关闭窗口并启动主程序
            self.root.after(1500, self.on_verification_success)
        else:
            self.status_var.set(f"❌ {message}")
            self.status_label.config(fg="#ef4444")
            self.verify_btn.config(state=tk.NORMAL)

    def on_verification_success(self):
        """验证成功后的处理"""
        if self.on_success:
            self.on_success(self.license_data)
        self.root.destroy()

    def run(self):
        """运行 GUI"""
        self.create_window()
        self.root.mainloop()
        return self.license_data


def show_license_verification(on_success: Optional[Callable] = None):
    """
    显示 License 验证窗口

    Args:
        on_success: 验证成功后的回调函数

    Returns:
        license 数据（如果验证成功）
    """
    # 如果 tkinter 不可用，使用命令行模式
    if not TKINTER_AVAILABLE:
        return console_license_verification(on_success)

    gui = LicenseVerificationGUI(on_success)
    return gui.run()


def console_license_verification(on_success: Optional[Callable] = None):
    """
    命令行模式的 License 验证

    Args:
        on_success: 验证成功后的回调函数

    Returns:
        license 数据（如果验证成功）
    """
    print()
    print("=" * 50)
    print("  B站评论助手 - License 验证")
    print("=" * 50)
    print()

    # 尝试自动加载 license
    default_paths = [
        "./license.lic",
        "./License.lic",
        os.path.join(os.path.dirname(sys.executable), "license.lic"),
    ]

    license_path = None
    for path in default_paths:
        if os.path.exists(path):
            license_path = path
            print(f"[*] 找到 License 文件: {path}")
            break

    if not license_path:
        print("[!] 未找到 License 文件")
        print()
        print("请将 license.lic 文件放在以下任一位置:")
        for path in default_paths:
            print(f"  - {os.path.abspath(path)}")
        print()
        print("或手动输入 License 文件路径:")
        license_path = input("路径: ").strip().strip('"')

        if not license_path or not os.path.exists(license_path):
            print()
            print("[X] License 文件不存在，程序无法启动")
            print()
            return None

    # 验证 license
    print()
    print("[*] 正在验证 License...")
    valid, message, data = validate_license(license_path)

    print()
    if valid:
        print("[OK] 验证成功!")
        print()
        print("License 信息:")
        print(f"  用户: {data.get('user', 'N/A')}")
        print(f"  类型: {data.get('type', '标准版')}")
        if data.get('expire_date'):
            print(f"  到期时间: {data.get('expire_date', 'N/A')}")
        else:
            print(f"  有效期: 永久")
        if data.get('notes'):
            print(f"  备注: {data.get('notes')}")
        print()
        print("[*] 正在启动程序...")
        print()

        if on_success:
            on_success(data)

        return data
    else:
        print(f"[ERROR] 验证失败: {message}")
        print()
        print("请联系发行方获取有效的 License 文件")
        print()
        return None


if __name__ == "__main__":
    # 测试
    data = show_license_verification()
    if data:
        print(f"验证成功: {data}")
    else:
        print("验证失败或取消")
