from utils.logger import get_logger

logger = get_logger()


class CaptchaNotifier:
    """验证码通知接口（预留扩展）

    当前仅通过日志输出通知信息。
    后续可通过继承此类并重写 notify() 方法来接入：
    - 微信推送（如 Server酱、PushPlus）
    - Telegram Bot
    - 邮件通知
    - 桌面弹窗
    - 等其他通知渠道
    """

    def notify(self, count: int, cooldown_minutes: int, quiet_minutes: int = 5):
        """当检测到验证码时调用

        Args:
            count: 今日第几次触发验证码
            cooldown_minutes: 即将进入的养号冷却时长（分钟）
            quiet_minutes: 静默等待时长（分钟）
        """
        total_wait = quiet_minutes + cooldown_minutes
        logger.warning(
            f"[通知] 触发验证码（今日第{count}次），"
            f"即将静默{quiet_minutes}分钟 + 养号{cooldown_minutes}分钟，"
            f"共计等待约{total_wait}分钟后恢复评论任务"
        )

    def notify_terminated(self, count: int, max_count: int):
        """当验证码次数达到上限、任务终止时调用

        Args:
            count: 今日触发次数
            max_count: 配置的上限
        """
        logger.error(
            f"[通知] 今日验证码触发已达上限（{count}/{max_count}），"
            f"任务已终止。建议明天再试或检查账号状态。"
        )
