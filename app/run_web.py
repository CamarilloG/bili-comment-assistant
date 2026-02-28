"""
Web 版 exe 入口：启动 uvicorn 并自动用系统默认浏览器打开控制台页面。
供 PyInstaller 打包为单文件 exe 时使用。
uvicorn 必须在主线程运行，否则 frozen 下子线程无法正确解析打包的 web 模块。
"""
import os
import sys
import traceback

# 立即设置控制台编码为 UTF-8（在任何输出之前）
if os.name == "nt":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except:
        pass


def _verify_license() -> bool:
    """
    验证 License

    Returns:
        是否验证成功
    """
    try:
        from license.gui import show_license_verification

        # 显示验证窗口
        license_data = show_license_verification()

        if license_data:
            print(f"[License] 验证成功 - 用户: {license_data.get('user', 'N/A')}")
            return True
        else:
            print("[License] 验证失败或取消")
            return False

    except ImportError as e:
        print(f"[License] 警告: 无法加载 License 验证模块: {e}")
        print("[License] 跳过验证，继续启动...")
        return True
    except Exception as e:
        print(f"[License] 验证过程出错: {e}")
        return False


def _set_windows_console_utf8() -> None:
    """在 Windows 下将控制台编码切换为 UTF-8，尽量避免中文输出乱码。"""
    if os.name != "nt":
        return
    try:
        import ctypes

        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:
        # 若切换失败则静默忽略，避免影响主流程
        pass


# 工作目录：frozen 时用 exe 所在目录（config.yaml、cookies.json 等放同目录）
if getattr(sys, "frozen", False):
    app_base = os.path.dirname(sys.executable)
    os.chdir(app_base)
    # PyInstaller onefile: 源码会被解压到 sys._MEIPASS/app 下，这里显式加入 sys.path 以便导入 web.app 等包
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

# 尝试切换控制台编码为 UTF-8，减少中文乱码
_set_windows_console_utf8()

PORT = 9527


def _excepthook(typ, value, tb):
    """未捕获异常时输出并暂停，避免闪退。"""
    traceback.print_exception(typ, value, tb)
    if getattr(sys, "frozen", False):
        log_path = os.path.join(app_base, "run_web_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                traceback.print_exception(typ, value, tb, file=f)
            print(f"\n错误已写入: {log_path}", flush=True)
        except Exception:
            pass
        input("\n按回车键退出...")


def _get_windows_default_browser_path() -> str | None:
    """从 Windows 注册表读取默认浏览器可执行文件路径，失败返回 None。"""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        # 先读 UserChoice 得到 ProgId（如 ChromeHTML、MSEdgeHTM）
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice",
                0,
                winreg.KEY_READ,
            )
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            winreg.CloseKey(key)
        except OSError:
            # 回退：直接读 http\shell\open\command
            key = winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT,
                r"http\shell\open\command",
                0,
                winreg.KEY_READ,
            )
            cmd, _ = winreg.QueryValueEx(key, None)
            winreg.CloseKey(key)
            return _parse_browser_command(cmd)

        # 根据 ProgId 读打开命令
        key = winreg.OpenKey(
            winreg.HKEY_CLASSES_ROOT,
            rf"{prog_id}\shell\open\command",
            0,
            winreg.KEY_READ,
        )
        cmd, _ = winreg.QueryValueEx(key, None)
        winreg.CloseKey(key)
        return _parse_browser_command(cmd)
    except Exception:
        return None


def _parse_browser_command(cmd: str) -> str | None:
    """从注册表命令字符串中解析出 exe 路径（支持带空格的 quoted path、%ProgramFiles% 等）。"""
    if not cmd or not cmd.strip():
        return None
    cmd = cmd.strip()
    path = None
    if cmd.startswith('"'):
        end = cmd.find('"', 1)
        if end != -1:
            path = cmd[1:end].strip()
    else:
        first = cmd.split(None, 1)[0] if cmd else ""
        path = first
    if not path:
        return None
    path = os.path.expandvars(path)
    if os.path.isfile(path):
        return os.path.normpath(path)
    return None


def _ensure_exe_config_files():
    """首次运行时在 exe 同目录创建所需配置文件（仅 frozen 时调用）。"""
    config_path = os.path.join(app_base, "config.yaml")
    if not os.path.exists(config_path):
        try:
            from core.config import ConfigValidator
            ConfigValidator.load_config(config_path)
        except Exception:
            pass

    # 若配置里浏览器路径为空，尝试写入系统默认浏览器路径（仅 Windows）
    try:
        from core.config import ConfigValidator
        config = ConfigValidator.load_config(config_path)
        if not (config.get("browser") or {}).get("path", "").strip():
            browser_path = _get_windows_default_browser_path()
            if browser_path:
                config.setdefault("browser", {})["path"] = browser_path
                ConfigValidator.save_config(config, config_path)
    except Exception:
        pass

    cookies_path = os.path.join(app_base, "cookies.json")
    if not os.path.exists(cookies_path):
        try:
            with open(cookies_path, "w", encoding="utf-8") as f:
                f.write("[]")
        except Exception:
            pass


def _fatal(err_msg: str, exc: BaseException | None = None):
    """闪退时输出错误并暂停，便于查看；frozen 时同时写入同目录日志。"""
    lines = [err_msg]
    if exc is not None:
        lines.append(traceback.format_exc())
    text = "\n".join(lines)
    print(text, flush=True)
    if getattr(sys, "frozen", False):
        log_path = os.path.join(app_base, "run_web_error.log")
        try:
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"\n错误已写入: {log_path}", flush=True)
        except Exception:
            pass
        input("\n按回车键退出...")
    sys.exit(1)


def main():
    try:
        # License 验证
        if not _verify_license():
            _fatal("License 验证失败，程序无法启动")
            return

        if getattr(sys, "frozen", False):
            _ensure_exe_config_files()
        # 显式导入 web.app：让 PyInstaller 收集到该包，并避免字符串导入在打包环境下找不到 web
        import web.app  # type: ignore[import-not-found]
        import uvicorn
        # 关闭请求日志，终端仅显示下方 lifespan 中的中文启动提示
        log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "loggers": {
                "uvicorn": {"level": "CRITICAL"},
                "uvicorn.access": {"level": "CRITICAL"},
            },
        }
        uvicorn.run(
            web.app.app,
            host="0.0.0.0",
            port=PORT,
            access_log=False,
            log_config=log_config,
        )
    except Exception as e:
        _fatal(f"启动失败: {e}", e)


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        sys.excepthook = _excepthook
    try:
        main()
    except Exception as e:
        _fatal(f"启动失败: {e}", e)
