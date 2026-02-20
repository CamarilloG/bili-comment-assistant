import json
import re
from core.ai_provider import AIProvider
from core.prompts import COMMENT_SYSTEM, COMMENT_USER, FILTER_SYSTEM, FILTER_USER
from utils.logger import get_logger

logger = get_logger()


class AIManager:

    def __init__(self, config: dict):
        self.config = config
        ai_cfg = config.get("ai", {})
        self.provider = AIProvider(config) if ai_cfg.get("enabled") else None
        self._comment_cfg = ai_cfg.get("comment", {})
        self._filter_cfg = ai_cfg.get("filter", {})

    def is_comment_enabled(self) -> bool:
        return self.provider is not None and self._comment_cfg.get("enabled", False)

    def is_filter_enabled(self) -> bool:
        return (
            self.provider is not None
            and self._filter_cfg.get("enabled", False)
            and bool(self._filter_cfg.get("criteria", "").strip())
        )

    def generate_comment(self, video_info: dict) -> str | None:
        if not self.is_comment_enabled():
            return None

        system_prompt = COMMENT_SYSTEM.format(
            user_intent=self._comment_cfg.get("user_intent", "") or "普通B站用户",
            style=self._comment_cfg.get("style", "casual"),
            max_length=self._comment_cfg.get("max_length", 100),
        )
        user_prompt = COMMENT_USER.format(
            title=video_info.get("title", ""),
            author=video_info.get("author", ""),
        )

        raw = self.provider.chat(system_prompt, user_prompt)
        if not raw:
            return None

        text = self._clean_comment(raw)
        if not text:
            logger.warning(f"[AI] 评论清洗后为空，原始内容: {raw[:80]}")
            return None

        max_len = self._comment_cfg.get("max_length", 100)
        if len(text) > max_len:
            text = text[:max_len]

        return text

    def check_video_relevance(self, video_info: dict) -> tuple[bool, str]:
        if not self.is_filter_enabled():
            return True, ""

        system_prompt = FILTER_SYSTEM.format(
            criteria=self._filter_cfg.get("criteria", ""),
        )
        user_prompt = FILTER_USER.format(
            title=video_info.get("title", ""),
            author=video_info.get("author", ""),
            views=video_info.get("views", ""),
            date=video_info.get("date", ""),
        )

        raw = self.provider.chat(system_prompt, user_prompt)
        if not raw:
            return True, "AI 调用失败，默认保留"

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(cleaned)
            keep = bool(data.get("keep", True))
            reason = str(data.get("reason", ""))
            return keep, reason
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[AI] 筛选结果解析失败: {e} | 原始: {raw[:120]}")
            return True, "解析失败，默认保留"

    @staticmethod
    def _clean_comment(text: str) -> str:
        text = text.strip().strip('"').strip("'").strip(""").strip(""")
        prefixes = ["以下是评论：", "以下是评论:", "评论：", "评论:", "评论内容：", "评论内容:"]
        for p in prefixes:
            if text.startswith(p):
                text = text[len(p):].strip()
        return text
