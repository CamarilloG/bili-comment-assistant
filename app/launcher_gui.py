"""
统一 GUI 启动器：集成 License 验证 + 后端启动 + 前端界面
"""
import os
import sys
import threading
import time
import webbrowser
import traceback
from pathlib import Path
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import tkinter as tk
from tkinter import messagebox, filedialog

# 设置控制台编码
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except:
        pass

# 工作目录设置
if getattr(sys, "frozen", False):
    app_base = os.path.dirname(sys.executable)
    os.chdir(app_base)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        app_src = os.path.join(meipass, "app")
        if os.path.isdir(app_src) and app_src not in sys.path:
            sys.path.insert(0, app_src)
else:
    app_base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_base)
    if app_base not in sys.path:
        sys.path.insert(0, app_base)

PORT = 9527


class LauncherGUI:
    """统一启动器 GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("Bilibili Bot 启动器")
        self.center_window(700, 550)

        self.backend_thread = None
        self.backend_running = False
        self.backend_server = None  # uvicorn server 实例
        self.license_verified = False
        self.license_path = None
        self.license_data = None

        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 启动时自动查找 License
        self.root.after(500, self.auto_load_license)

    def center_window(self, width, height):
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def setup_ui(self):
        # 主容器
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=BOTH, expand=YES)

        # 标题
        title_label = ttk.Label(
            main_frame,
            text="Bilibili Bot 启动器",
            font=("Microsoft YaHei UI", 20, "bold"),
            bootstyle="primary"
        )
        title_label.pack(pady=(0, 20))

        # License 验证区域
        license_frame = ttk.LabelFrame(main_frame, text="License 验证")
        license_frame.pack(fill=X, pady=(0, 15))
        license_inner = ttk.Frame(license_frame, padding=15)
        license_inner.pack(fill=BOTH, expand=YES)

        # License 文件路径
        path_frame = ttk.Frame(license_inner)
        path_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(path_frame, text="License 文件:", width=12).pack(side=LEFT)
        self.license_path_var = tk.StringVar(value="未选择")
        ttk.Label(
            path_frame,
            textvariable=self.license_path_var,
            bootstyle="secondary",
            font=("Consolas", 9)
        ).pack(side=LEFT, fill=X, expand=YES, padx=(5, 0))

        # License 按钮
        btn_frame = ttk.Frame(license_inner)
        btn_frame.pack(fill=X, pady=(0, 10))

        self.select_license_btn = ttk.Button(
            btn_frame,
            text="选择 License",
            command=self.select_license_file,
            bootstyle="info-outline",
            width=15
        )
        self.select_license_btn.pack(side=LEFT, padx=(0, 5))

        self.verify_license_btn = ttk.Button(
            btn_frame,
            text="验证 License",
            command=self.verify_license,
            bootstyle="success",
            width=15,
            state=DISABLED
        )
        self.verify_license_btn.pack(side=LEFT)

        # License 状态
        status_frame = ttk.Frame(license_inner)
        status_frame.pack(fill=X)
        ttk.Label(status_frame, text="验证状态:", width=12).pack(side=LEFT)
        self.license_status = ttk.Label(
            status_frame,
            text="未验证",
            bootstyle="warning"
        )
        self.license_status.pack(side=LEFT)

        # 服务控制区域
        service_frame = ttk.LabelFrame(main_frame, text="服务控制")
        service_frame.pack(fill=X, pady=(0, 15))
        service_inner = ttk.Frame(service_frame, padding=15)
        service_inner.pack(fill=BOTH, expand=YES)

        # 后端状态
        backend_frame = ttk.Frame(service_inner)
        backend_frame.pack(fill=X, pady=(0, 10))
        ttk.Label(backend_frame, text="后端服务:", width=12).pack(side=LEFT)
        self.backend_status = ttk.Label(
            backend_frame,
            text="未启动",
            bootstyle="secondary"
        )
        self.backend_status.pack(side=LEFT)

        # 服务按钮
        service_btn_frame = ttk.Frame(service_inner)
        service_btn_frame.pack(fill=X)

        self.start_btn = ttk.Button(
            service_btn_frame,
            text="启动服务",
            command=self.start_backend,
            bootstyle="success",
            width=15,
            state=DISABLED
        )
        self.start_btn.pack(side=LEFT, padx=(0, 5))

        self.open_web_btn = ttk.Button(
            service_btn_frame,
            text="打开 Web 面板",
            command=self.open_web_panel,
            bootstyle="info",
            width=15,
            state=DISABLED
        )
        self.open_web_btn.pack(side=LEFT, padx=(0, 5))

        self.stop_btn = ttk.Button(
            service_btn_frame,
            text="停止服务",
            command=self.stop_backend,
            bootstyle="danger",
            width=15,
            state=DISABLED
        )
        self.stop_btn.pack(side=LEFT)

        # 日志显示区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志")
        log_frame.pack(fill=BOTH, expand=YES)
        log_inner = ttk.Frame(log_frame, padding=10)
        log_inner.pack(fill=BOTH, expand=YES)

        self.log_area = tk.Text(
            log_inner,
            height=10,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#f8f9fa",
            fg="#212529"
        )
        self.log_area.pack(fill=BOTH, expand=YES)

    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_area.see(tk.END)
        self.root.update_idletasks()

    def auto_load_license(self):
        """自动加载 License 文件"""
        default_paths = [
            "./license.lic",
            "./License.lic",
            os.path.join(os.path.dirname(sys.executable), "license.lic"),
            os.path.join(app_base, "license.lic"),
        ]

        for path in default_paths:
            if os.path.exists(path):
                self.license_path = path
                self.license_path_var.set(Path(path).name)
                self.verify_license_btn.config(state=NORMAL)
                self.log(f"找到 License 文件: {Path(path).name}")
                # 自动验证
                self.root.after(500, self.verify_license)
                return

        self.log("未找到 License 文件，请手动选择")

    def select_license_file(self):
        """选择 License 文件"""
        file_path = filedialog.askopenfilename(
            title="选择 License 文件",
            filetypes=[
                ("License 文件", "*.lic"),
                ("所有文件", "*.*")
            ]
        )

        if file_path:
            self.license_path = file_path
            self.license_path_var.set(Path(file_path).name)
            self.verify_license_btn.config(state=NORMAL)
            self.log(f"已选择: {Path(file_path).name}")

    def verify_license(self):
        """验证 License"""
        if not self.license_path:
            messagebox.showwarning("提示", "请先选择 License 文件")
            return

        self.log("正在验证 License...")
        self.verify_license_btn.config(state=DISABLED)
        self.root.update()

        try:
            from license.validator import validate_license

            valid, message, data = validate_license(self.license_path)

            if valid:
                self.license_data = data
                user = data.get('user', 'N/A')
                self.log(f"License 验证成功 - 用户: {user}")
                self.license_status.config(text=f"已验证 ✓ ({user})", bootstyle="success")
                self.license_verified = True
                self.start_btn.config(state=NORMAL)
            else:
                self.log(f"License 验证失败: {message}")
                self.license_status.config(text="验证失败 ✗", bootstyle="danger")
                self.license_verified = False
                self.verify_license_btn.config(state=NORMAL)
                messagebox.showerror("验证失败", f"License 验证失败:\n{message}")

        except ImportError as e:
            self.log(f"警告: 无法加载 License 验证模块: {e}")
            self.log("跳过验证，继续启动...")
            self.license_status.config(text="已跳过", bootstyle="info")
            self.license_verified = True
            self.start_btn.config(state=NORMAL)

        except Exception as e:
            self.log(f"验证过程出错: {e}")
            self.license_status.config(text="验证失败 ✗", bootstyle="danger")
            self.license_verified = False
            self.verify_license_btn.config(state=NORMAL)
            messagebox.showerror("验证错误", f"License 验证出错:\n{e}")

    def start_backend(self):
        """启动后端服务"""
        if not self.license_verified:
            messagebox.showwarning("未验证", "请先完成 License 验证")
            return

        if self.backend_running:
            messagebox.showinfo("提示", "后端服务已在运行中")
            return

        # 检查后端线程是否还在运行
        if self.backend_thread and self.backend_thread.is_alive():
            messagebox.showwarning("提示", "后端服务正在停止中，请稍后再试")
            return

        # 检查端口是否被占用
        if self._is_port_in_use(PORT):
            self.log(f"错误: 端口 {PORT} 已被占用")
            response = messagebox.askyesno(
                "端口占用",
                f"端口 {PORT} 已被占用\n\n可能是上次服务未完全关闭\n是否等待 3 秒后重试？"
            )
            if response:
                self.log("等待 3 秒后重试...")
                self.root.after(3000, self.start_backend)
            return

        self.log("正在启动后端服务...")
        self.start_btn.config(state=DISABLED)

        # 在新线程中启动后端
        self.backend_thread = threading.Thread(target=self._run_backend, daemon=True)
        self.backend_thread.start()

        # 轮询等待后端启动（import web.app 等可能需数秒）
        self._backend_check_count = 0
        self._backend_check_max = 10  # 最多等约 15 秒
        self.root.after(1500, self._check_backend_started)

    def _is_port_in_use(self, port):
        """检查端口是否被占用"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", port))
                return False
            except OSError:
                return True

    def _run_backend(self):
        """在后台线程运行后端服务"""
        try:
            self.root.after(0, lambda: self.log("正在导入 web.app 模块..."))
            import web.app
            self.root.after(0, lambda: self.log("正在导入 uvicorn 模块..."))
            import uvicorn

            log_config = {
                "version": 1,
                "disable_existing_loggers": False,
                "loggers": {
                    "uvicorn": {"level": "CRITICAL"},
                    "uvicorn.access": {"level": "CRITICAL"},
                },
            }

            self.root.after(0, lambda: self.log("正在创建 uvicorn 配置..."))
            # 创建 uvicorn 配置
            config = uvicorn.Config(
                web.app.app,
                host="0.0.0.0",
                port=PORT,
                access_log=False,
                log_config=log_config,
            )

            self.root.after(0, lambda: self.log("正在创建 uvicorn server..."))
            # 创建 server 实例
            self.backend_server = uvicorn.Server(config)
            self.backend_running = True

            self.root.after(0, lambda: self.log("正在启动 uvicorn server..."))
            # 运行 server（阻塞）
            self.backend_server.run()

            # Server 正常退出
            self.root.after(0, lambda: self.log("uvicorn server 已退出"))

        except ImportError as e:
            self.backend_running = False
            err_short = f"后端导入失败: {e}"
            error_msg = f"{err_short}\n模块路径: {sys.path}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self.log(err_short))
            self.root.after(0, lambda: self.log(error_msg))
            self.root.after(0, lambda: messagebox.showerror("导入失败", f"后端模块导入失败:\n{e}\n\n请检查是否缺少依赖库"))
            traceback.print_exc()
        except Exception as e:
            self.backend_running = False
            err_short = f"后端启动失败: {e}"
            error_msg = f"{err_short}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self.log(err_short))
            self.root.after(0, lambda: self.log(error_msg))
            self.root.after(0, lambda: messagebox.showerror("启动失败", f"后端服务启动失败:\n{e}"))
            traceback.print_exc()
        finally:
            # 确保清理状态
            self.backend_running = False
            if self.backend_server:
                try:
                    # 确保 server 完全关闭
                    self.backend_server.should_exit = True
                except Exception:
                    pass
            self.backend_server = None
            self.root.after(0, lambda: self.log("后端线程已清理完成"))

    def _check_backend_started(self):
        """轮询检查后端是否启动成功"""
        if self.backend_running:
            # 实际检查端口是否可访问
            import socket
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    s.connect(("127.0.0.1", PORT))
                # 端口可访问，后端已启动
                url = f"http://localhost:{PORT}/panel/"
                self.log("后端服务已启动")
                self.log("请访问以下地址进入控制台:")
                self.log(f"  {url}")
                self.backend_status.config(text="运行中 ✓", bootstyle="success")
                self.stop_btn.config(state=NORMAL)
                self.open_web_btn.config(state=NORMAL)
                self.root.after(500, self.open_web_panel)
                return
            except (socket.error, socket.timeout):
                # 端口还未就绪，继续等待
                pass

        self._backend_check_count = getattr(self, "_backend_check_count", 0) + 1
        if self._backend_check_count >= getattr(self, "_backend_check_max", 10):
            self.log("后端服务启动失败（超时或启动过程出错，请查看上方日志）")
            self.backend_running = False
            self.start_btn.config(state=NORMAL)
            return
        # 每 1.5 秒再检查一次
        self.root.after(1500, self._check_backend_started)

    def open_web_panel(self):
        """打开 Web 面板"""
        url = f"http://localhost:{PORT}/panel/"
        self.log(f"正在打开 Web 面板: {url}")

        try:
            webbrowser.open(url)
            self.log("Web 面板已在浏览器中打开")
        except Exception as e:
            self.log(f"打开浏览器失败: {e}")
            messagebox.showerror("打开失败", f"无法打开浏览器:\n{e}\n\n请手动访问: {url}")

    def stop_backend(self):
        """停止后端服务"""
        self.log("正在停止后端服务...")
        self.stop_btn.config(state=DISABLED)

        # 设置停止标志
        self.backend_running = False

        # 停止 uvicorn server
        if self.backend_server:
            try:
                self.backend_server.should_exit = True
                self.log("已发送停止信号到后端服务")
            except Exception as e:
                self.log(f"停止服务时出错: {e}")

        # 等待后端线程结束
        if self.backend_thread and self.backend_thread.is_alive():
            self.log("等待后端线程结束...")
            # 在新线程中等待，避免阻塞 GUI
            def wait_thread():
                try:
                    # 增加超时时间到 10 秒，uvicorn 需要时间优雅关闭
                    self.backend_thread.join(timeout=10)
                    if self.backend_thread.is_alive():
                        self.root.after(0, lambda: self.log("警告: 后端线程未能在 10 秒内结束，已强制继续"))
                        self.root.after(0, lambda: self.log("提示: 如需重启，请等待几秒后再点击启动"))
                    else:
                        self.root.after(0, lambda: self.log("后端线程已正常结束"))
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"等待线程时出错: {e}"))
                finally:
                    self.root.after(0, self._finish_stop)

            threading.Thread(target=wait_thread, daemon=True).start()
        else:
            self._finish_stop()

    def _finish_stop(self):
        """完成停止操作，更新 UI"""
        self.backend_status.config(text="已停止", bootstyle="secondary")
        self.open_web_btn.config(state=DISABLED)
        self.start_btn.config(state=NORMAL)
        self.log("后端服务已停止")

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.backend_running:
            if messagebox.askokcancel("确认退出", "后端服务正在运行，确定要退出吗？"):
                self.backend_running = False
                # 停止 uvicorn server
                if self.backend_server:
                    try:
                        self.backend_server.should_exit = True
                    except Exception:
                        pass
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    """主函数"""
    try:
        # 确保配置文件存在
        if getattr(sys, "frozen", False):
            from core.slot import get_config_path, ensure_slot_dir
            ensure_slot_dir("0")
            config_path = get_config_path("0")
            if not os.path.exists(config_path):
                try:
                    from core.config import ConfigValidator
                    ConfigValidator.load_config(config_path)
                except Exception:
                    pass

        # 创建 GUI
        app = ttk.Window(themename="cosmo")
        gui = LauncherGUI(app)
        app.mainloop()

    except Exception as e:
        print(f"启动器启动失败: {e}")
        traceback.print_exc()
        if getattr(sys, "frozen", False):
            input("\n按回车键退出...")


if __name__ == "__main__":
    main()
