import os
import json
from datetime import datetime
from utils.logger import get_logger

logger = get_logger()


class CaptchaTracker:
    """持久化记录每日验证码触发次数"""

    def __init__(self, file_path="captcha_record.json"):
        self.file_path = file_path
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 如果日期是今天，返回已有数据；否则重置
                    if data.get("date") == self._today():
                        return data
            except (json.JSONDecodeError, IOError, ValueError) as e:
                logger.warning(f"读取验证码记录文件失败: {e}，将重新创建")
        return {"date": self._today(), "count": 0}

    def _save(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False)
        except IOError as e:
            logger.error(f"保存验证码记录失败: {e}")

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _ensure_today(self):
        """如果日期已过，自动重置计数"""
        if self._data.get("date") != self._today():
            self._data = {"date": self._today(), "count": 0}

    def record(self) -> int:
        """记录一次验证码触发，返回今日累计次数"""
        self._ensure_today()
        self._data["count"] += 1
        self._save()
        logger.warning(f"[风控] 验证码触发已记录，今日累计: {self._data['count']} 次")
        return self._data["count"]

    def get_today_count(self) -> int:
        """获取今日验证码触发次数"""
        self._ensure_today()
        return self._data["count"]

    def get_cooldown_minutes(self, base_minutes: int = 30) -> int:
        """根据今日触发次数计算养号冷却时长（分钟）"""
        self._ensure_today()
        return self._data["count"] * base_minutes
