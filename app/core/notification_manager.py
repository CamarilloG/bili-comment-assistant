"""
全局通知系统
支持 Web 端吐司通知和 Windows 系统通知
"""
import os
import sys
from typing import Literal
from utils.logger import get_logger

logger = get_logger()

NotificationType = Literal["info", "warning", "error", "captcha", "critical"]


class NotificationManager:
    """全局通知管理器"""

    def __init__(self):
        self._web_callbacks = []  # Web 端通知回调
        self._failure_counts = {}  # 记录每个实例的连续失败次数

    def register_web_callback(self, callback):
        """注册 Web 端通知回调"""
        if callback not in self._web_callbacks:
            self._web_callbacks.append(callback)

    def unregister_web_callback(self, callback):
        """注销 Web 端通知回调"""
        if callback in self._web_callbacks:
            self._web_callbacks.remove(callback)

    def send_notification(
        self,
        title: str,
        message: str,
        notification_type: NotificationType = "info",
        slot_id: str = "0",
        show_system: bool = False,
    ):
        """
        发送通知

        Args:
            title: 通知标题
            message: 通知内容
            notification_type: 通知类型
            slot_id: 实例 ID
            show_system: 是否显示系统通知
        """
        # 记录日志
        log_message = f"[实例 {slot_id}] {title}: {message}"
        if notification_type == "error" or notification_type == "critical":
            logger.error(log_message)
        elif notification_type == "warning" or notification_type == "captcha":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # 发送 Web 通知
        self._send_web_notification(title, message, notification_type, slot_id)

        # 发送系统通知（仅重要通知）
        if show_system:
            self._send_system_notification(title, message, notification_type)

    def notify_captcha(self, slot_id: str, count: int, cooldown_minutes: int):
        """验证码通知"""
        title = f"实例 {slot_id} 检测到验证码"
        message = f"今日第 {count} 次触发，将冷却 {cooldown_minutes} 分钟"
        self.send_notification(
            title=title,
            message=message,
            notification_type="captcha",
            slot_id=slot_id,
            show_system=True,  # 验证码必须显示系统通知
        )

    def notify_failure(self, slot_id: str, reason: str):
        """记录失败，连续 3 次失败时发送通知"""
        if slot_id not in self._failure_counts:
            self._failure_counts[slot_id] = 0

        self._failure_counts[slot_id] += 1
        count = self._failure_counts[slot_id]

        if count >= 3:
            title = f"实例 {slot_id} 连续失败"
            message = f"已连续失败 {count} 次：{reason}"
            self.send_notification(
                title=title,
                message=message,
                notification_type="critical",
                slot_id=slot_id,
                show_system=True,  # 连续失败显示系统通知
            )

    def reset_failure_count(self, slot_id: str):
        """重置失败计数（成功时调用）"""
        if slot_id in self._failure_counts:
            self._failure_counts[slot_id] = 0

    def notify_terminated(self, slot_id: str, reason: str):
        """任务终止通知"""
        title = f"实例 {slot_id} 任务终止"
        message = reason
        self.send_notification(
            title=title,
            message=message,
            notification_type="critical",
            slot_id=slot_id,
            show_system=True,  # 任务终止显示系统通知
        )

    def _send_web_notification(
        self, title: str, message: str, notification_type: NotificationType, slot_id: str
    ):
        """发送 Web 端通知"""
        import time

        notification_data = {
            "title": title,
            "message": message,
            "type": notification_type,
            "slot_id": slot_id,
            "timestamp": time.time(),
        }

        # 调用所有注册的回调
        for callback in self._web_callbacks:
            try:
                callback(notification_data)
            except Exception as e:
                logger.error(f"Web 通知回调失败: {e}")

        # 通过 WebSocket 广播通知
        try:
            from web.routers.notification_api import broadcast_notification
            broadcast_notification(notification_data)
        except Exception as e:
            logger.debug(f"WebSocket 通知广播失败（可能 Web 服务未启动）: {e}")

    def _send_system_notification(
        self, title: str, message: str, notification_type: NotificationType
    ):
        """发送 Windows 系统通知"""
        try:
            # 仅在 Windows 系统上发送通知
            if sys.platform != "win32":
                return

            # 使用 plyer 库发送通知（如果可用）
            try:
                from plyer import notification

                # 根据类型选择图标
                icon_path = None
                if notification_type in ["error", "critical"]:
                    icon_type = "error"
                elif notification_type == "warning":
                    icon_type = "warning"
                elif notification_type == "captcha":
                    icon_type = "warning"
                else:
                    icon_type = "info"

                notification.notify(
                    title=title,
                    message=message,
                    app_name="Bilibili Bot",
                    timeout=10,  # 10 秒后自动消失
                )
                logger.debug(f"系统通知已发送: {title}")
            except ImportError:
                # plyer 不可用，使用 Windows 原生通知
                self._send_windows_toast(title, message)
        except Exception as e:
            logger.error(f"发送系统通知失败: {e}")

    def _send_windows_toast(self, title: str, message: str):
        """使用 Windows 原生 Toast 通知"""
        try:
            # 使用 win10toast 库
            from win10toast import ToastNotifier

            toaster = ToastNotifier()
            toaster.show_toast(
                title=title,
                msg=message,
                duration=10,
                threaded=True,  # 非阻塞
            )
        except ImportError:
            logger.debug("win10toast 不可用，跳过系统通知")
        except Exception as e:
            logger.error(f"Windows Toast 通知失败: {e}")


# 全局单例
_notification_manager = None


def get_notification_manager() -> NotificationManager:
    """获取全局通知管理器"""
    global _notification_manager
    if _notification_manager is None:
        _notification_manager = NotificationManager()
    return _notification_manager
