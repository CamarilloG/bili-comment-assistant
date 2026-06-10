"""百度内部通讯机器人通知模块"""

import requests
from typing import Optional
from utils.logger import get_logger

logger = get_logger()


class BaiduBotNotifier:
    """百度内部通讯机器人通知器

    用于向百度内部通讯群组发送消息通知
    """

    def __init__(self, config: dict):
        """初始化百度机器人通知器

        Args:
            config: 配置字典，包含 api_url, access_token, group_id 等
        """
        self.enabled = config.get("enabled", False)
        self.api_url = config.get("api_url", "")
        self.access_token = config.get("access_token", "")
        self.group_id = config.get("group_id", "")
        self.notifications = config.get("notifications", {})

        # 验证配置
        if self.enabled:
            if not self.api_url or not self.access_token or not self.group_id:
                logger.warning("[百度机器人] 配置不完整，已禁用通知功能")
                self.enabled = False
            else:
                logger.info(f"[百度机器人] 已启用，群组 ID: {self.group_id}")

    def _should_notify(self, notification_type: str) -> bool:
        """检查是否应该发送指定类型的通知

        Args:
            notification_type: 通知类型，如 "captcha_alert"

        Returns:
            bool: 是否应该发送
        """
        if not self.enabled:
            return False
        return self.notifications.get(notification_type, True)

    def _send_message(self, content: str) -> bool:
        """发送消息到百度内部通讯群组

        Args:
            content: 消息内容

        Returns:
            bool: 是否发送成功
        """
        if not self.enabled:
            logger.debug("[百度机器人] 未启用，跳过发送")
            return False

        try:
            import json
            import os

            # 构造完整 URL
            url = f"{self.api_url}?access_token={self.access_token}"

            # 构造请求体（使用简化格式，与测试脚本一致）
            payload = {
                "message": {
                    "header": {
                        "toid": [int(self.group_id)]
                    },
                    "body": [
                        {
                            "type": "TEXT",
                            "content": content
                        }
                    ]
                }
            }

            # DEBUG: 详细日志
            logger.info(f"[百度机器人 DEBUG] 准备发送消息")
            logger.info(f"[百度机器人 DEBUG] API URL: {self.api_url}")
            logger.info(f"[百度机器人 DEBUG] Group ID: {self.group_id}")
            logger.info(f"[百度机器人 DEBUG] Access Token: {self.access_token[:10]}...{self.access_token[-10:]}")
            logger.info(f"[百度机器人 DEBUG] Payload: {json.dumps(payload, ensure_ascii=False)}")
            logger.info(f"[百度机器人 DEBUG] 系统代理 HTTP_PROXY: {os.environ.get('HTTP_PROXY', 'None')}")
            logger.info(f"[百度机器人 DEBUG] 系统代理 HTTPS_PROXY: {os.environ.get('HTTPS_PROXY', 'None')}")

            # 发送请求（使用系统代理，支持内网访问）
            # 注意：不指定 proxies 参数，requests 会自动使用系统代理
            logger.info(f"[百度机器人 DEBUG] 开始发送 POST 请求...")
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30  # 增加超时时间，适应内网环境
            )

            logger.info(f"[百度机器人 DEBUG] 收到响应: Status={response.status_code}")
            logger.info(f"[百度机器人 DEBUG] 响应头: {dict(response.headers)}")
            logger.info(f"[百度机器人 DEBUG] 响应体: {response.text[:500]}")

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[百度机器人 DEBUG] 解析 JSON: {result}")
                if result.get("errno") == 0:
                    logger.info(f"[百度机器人] 消息发送成功: {content[:50]}...")
                    return True
                else:
                    logger.error(f"[百度机器人] 消息发送失败: errno={result.get('errno')}, errmsg={result.get('errmsg')}")
                    return False
            else:
                logger.error(f"[百度机器人] 消息发送失败: HTTP {response.status_code}, Body: {response.text}")
                return False

        except requests.exceptions.Timeout as e:
            logger.error(f"[百度机器人] 请求超时（30秒）: {e}")
            return False
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[百度机器人] 连接错误: {e}")
            return False
        except Exception as e:
            logger.error(f"[百度机器人] 发送消息异常: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[百度机器人] 异常堆栈:\n{traceback.format_exc()}")
            return False

    # ========== 通知方法 ==========

    def notify_captcha_alert(self, source: str, detail: str = "", slot_id: int = 0):
        """验证码提醒

        Args:
            source: 触发场景，如 "comment" / "warmup"
            detail: 可选详情，如 BV 号、当前 URL
            slot_id: 实例 ID
        """
        if not self._should_notify("captcha_alert"):
            return

        source_name = {"comment": "评论", "warmup": "养号", "search": "搜索"}.get(source, source)
        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = f"🚨 验证码提醒\n\n{slot_info}在 {source_name} 过程中检测到验证码\n详情: {detail or '无'}\n\n请及时处理验证码，否则任务将暂停"
        self._send_message(message)

    def notify_captcha_cooldown(self, count: int, cooldown_minutes: int, quiet_minutes: int, slot_id: int = 0):
        """验证码冷却通知

        Args:
            count: 今日第几次触发验证码
            cooldown_minutes: 养号冷却时长（分钟）
            quiet_minutes: 静默等待时长（分钟）
            slot_id: 实例 ID
        """
        if not self._should_notify("captcha_cooldown"):
            return

        total_wait = quiet_minutes + cooldown_minutes
        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"⏸️ 验证码冷却\n\n"
            f"{slot_info}触发验证码（今日第 {count} 次）\n"
            f"静默等待: {quiet_minutes} 分钟\n"
            f"养号冷却: {cooldown_minutes} 分钟\n"
            f"预计恢复: 约 {total_wait} 分钟后"
        )
        self._send_message(message)

    def notify_captcha_terminated(self, count: int, max_count: int, slot_id: int = 0):
        """验证码达上限通知

        Args:
            count: 今日触发次数
            max_count: 配置的上限
            slot_id: 实例 ID
        """
        if not self._should_notify("captcha_terminated"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"🛑 任务终止\n\n"
            f"{slot_info}验证码触发已达上限\n"
            f"今日次数: {count}/{max_count}\n\n"
            f"建议明天再试或检查账号状态"
        )
        self._send_message(message)

    def notify_cd_limit(self, cd_warmup_hours: int, slot_id: int = 0):
        """CD 限制通知

        Args:
            cd_warmup_hours: CD 养号时长（小时）
            slot_id: 实例 ID
        """
        if not self._should_notify("cd_limit"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"⏸️ CD 限制触发\n\n"
            f"{slot_info}检测到 CD 限制\n"
            f"养号时长: {cd_warmup_hours} 小时\n\n"
            f"养号结束后任务将自动停止"
        )
        self._send_message(message)

    def notify_comment_success(self, video_title: str, comment_text: str, slot_id: int = 0):
        """评论成功通知（建议关闭，太频繁）

        Args:
            video_title: 视频标题
            comment_text: 评论内容
            slot_id: 实例 ID
        """
        if not self._should_notify("comment_success"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"✅ 评论成功\n\n"
            f"{slot_info}视频: {video_title[:30]}...\n"
            f"评论: {comment_text[:50]}..."
        )
        self._send_message(message)

    def notify_comment_failed(self, video_title: str, reason: str, slot_id: int = 0):
        """评论失败通知

        Args:
            video_title: 视频标题
            reason: 失败原因
            slot_id: 实例 ID
        """
        if not self._should_notify("comment_failed"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"❌ 评论失败\n\n"
            f"{slot_info}视频: {video_title[:30]}...\n"
            f"原因: {reason}"
        )
        self._send_message(message)

    def notify_task_started(self, task_type: str, target_count: int, slot_id: int = 0):
        """任务开始通知

        Args:
            task_type: 任务类型，如 "评论任务" / "养号任务"
            target_count: 目标数量
            slot_id: 实例 ID
        """
        if not self._should_notify("task_started"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"▶️ 任务开始\n\n"
            f"{slot_info}任务类型: {task_type}\n"
            f"目标数量: {target_count}"
        )
        self._send_message(message)

    def notify_task_completed(self, task_type: str, success_count: int, total_count: int, slot_id: int = 0):
        """任务完成通知

        Args:
            task_type: 任务类型
            success_count: 成功数量
            total_count: 总数量
            slot_id: 实例 ID
        """
        if not self._should_notify("task_completed"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"✅ 任务完成\n\n"
            f"{slot_info}任务类型: {task_type}\n"
            f"完成情况: {success_count}/{total_count}\n"
            f"成功率: {success_count/total_count*100:.1f}%" if total_count > 0 else "成功率: 0%"
        )
        self._send_message(message)

    def notify_task_error(self, task_type: str, error_message: str, slot_id: int = 0):
        """任务错误通知

        Args:
            task_type: 任务类型
            error_message: 错误信息
            slot_id: 实例 ID
        """
        if not self._should_notify("task_error"):
            return

        slot_info = f"[实例 {slot_id}] " if slot_id > 0 else ""

        message = (
            f"⚠️ 任务错误\n\n"
            f"{slot_info}任务类型: {task_type}\n"
            f"错误信息: {error_message[:100]}..."
        )
        self._send_message(message)

    def send_test_message(self) -> bool:
        """发送测试消息

        Returns:
            bool: 是否发送成功
        """
        message = "🤖 测试消息\n\n这是来自 Bilibili Bot 的测试通知\n\n如果收到此消息，说明配置成功！"
        return self._send_message(message)

