import sys
import os
import re
import contextvars
from loguru import logger

# 多槽位：任务线程内设置后，该线程产生的运行日志会带 slot_id，用于前端按实例展示
slot_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("slot_id", default=None)

# 获取日志目录：用户数据/logs
def _get_log_dir() -> str:
    """获取日志目录路径"""
    from core.slot import get_user_data_dir
    log_dir = os.path.join(get_user_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

_LOG_DIR = _get_log_dir()

def sanitize_log(record):
    message = record["message"]
    
    message = re.sub(r'SESSDATA=[^;]+', 'SESSDATA=***', message)
    message = re.sub(r'bili_jct=[^;]+', 'bili_jct=***', message)
    message = re.sub(r'DedeUserID=[^;]+', 'DedeUserID=***', message)
    message = re.sub(r'"password"\s*:\s*"[^"]+"', '"password": "***"', message)
    message = re.sub(r'"token"\s*:\s*"[^"]+"', '"token": "***"', message)
    message = re.sub(r'(sk-)[a-zA-Z0-9]{4}[a-zA-Z0-9]+', r'\g<1>****', message)
    message = re.sub(r'api_key["\s:=]+["\']?[a-zA-Z0-9_-]{8,}["\']?', 'api_key=***', message)
    
    record["message"] = message
    return True

logger.remove()
# 终端仅输出 WARNING 及以上，INFO 全部通过 WebSocket 在浏览器运行日志中查看
if sys.stderr:
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        filter=sanitize_log,
        level="WARNING",
    )
logger.add(
    os.path.join(_LOG_DIR, "bili_bot_{time:YYYY-MM-DD}.log"),
    rotation="10 MB",
    retention="10 days",
    encoding="utf-8",
    filter=sanitize_log
)


def _toast_sink(formatted: str) -> None:
    """WARNING 及以上时在 Windows 下弹出系统 Toast，带提示音。"""
    if sys.platform != "win32":
        return
    try:
        from winotify import Notification, audio
        level_name = "警告"
        if "ERROR" in formatted or "CRITICAL" in formatted:
            level_name = "错误"
        body = formatted.strip()
        if len(body) > 200:
            body = body[:197] + "..."
        toast = Notification(
            app_id="B站评论助手",
            title=f"B站评论助手 - {level_name}",
            msg=body,
        )
        # 使用系统提示音（winotify 的 audio 可选：Default / Mail 等）
        sound = getattr(audio, "Default", getattr(audio, "Mail", None))
        if sound is not None:
            toast.set_audio(sound, loop=False)
        toast.show()
    except Exception:
        pass


logger.add(
    _toast_sink,
    format="{level} | {message}",
    filter=sanitize_log,
    level="WARNING",
)

def get_logger():
    return logger
