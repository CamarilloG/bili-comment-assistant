"""
Web 版 exe 入口：启动 uvicorn 并自动用系统默认浏览器打开控制台页面。
供 PyInstaller 打包为单文件 exe 时使用。
uvicorn 必须在主线程运行，否则 frozen 下子线程无法正确解析打包的 web 模块。
"""
import os
import sys
import traceback

# 工作目录：frozen 时用 exe 所在目录（config.yaml、cookies.json 等放同目录）
if getattr(sys, "frozen", False):
    app_base = os.path.dirname(sys.executable)
    os.chdir(app_base)
else:
    app_base = os.path.dirname(os.path.abspath(__file__))
    os.chdir(app_base)
    if app_base not in sys.path:
        sys.path.insert(0, app_base)

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


def _ensure_exe_config_files():
    """首次运行时在 exe 同目录创建所需配置文件（仅 frozen 时调用）。"""
    config_path = os.path.join(app_base, "config.yaml")
    if not os.path.exists(config_path):
        try:
            from core.config import ConfigValidator
            ConfigValidator.load_config(config_path)
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
        if getattr(sys, "frozen", False):
            _ensure_exe_config_files()
        # 显式导入，让 PyInstaller 把 web 包及其依赖打进 exe；并直接传 app 对象，避免运行时再解析 "web.app:app"
        import web.app
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
