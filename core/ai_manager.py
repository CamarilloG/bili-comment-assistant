import json
import re
from core.ai_provider import AIProvider
from core.prompts import COMMENT_SYSTEM, COMMENT_USER, FILTER_SYSTEM, FILTER_USER
from utils.logger import get_logger

logger = get_logger()


SENSITIVITY_HINTS = {
    (1, 20): "当前为极度宽松模式：几乎不跳过任何视频，只有与筛选标准完全无关的才跳过。",
    (21, 40): "当前为宽松模式：关联度较低也保留，只跳过明显不相关的视频。",
    (41, 60): "当前为平衡模式：需要有一定关联度才保留，弱相关的根据语境综合判断。",
    (61, 80): "当前为严格模式：必须与筛选标准高度相关才保留，弱相关一律跳过。",
    (81, 100): "当前为极度严格模式：必须严格匹配关键词，且评论区也在讨论相关话题才保留，其余全部跳过。",
}


def get_sensitivity_hint(sensitivity: int) -> str:
    for (lo, hi), hint in SENSITIVITY_HINTS.items():
        if lo <= sensitivity <= hi:
            return hint
    return SENSITIVITY_HINTS[(41, 60)]


class AIManager:

    def __init__(self, config: dict, stop_event=None):
        self.config = config
        ai_cfg = config.get("ai", {})
        self.provider = AIProvider(config, stop_event) if ai_cfg.get("enabled") else None
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
            logger.warning("[AI] 评论功能未启用")
            return None

        system_prompt = COMMENT_SYSTEM.format(
            user_intent=self._comment_cfg.get("user_intent", "") or "普通B站用户",
            style=self._comment_cfg.get("style", "casual"),
            max_length=self._comment_cfg.get("max_length", 100),
            min_length=self._comment_cfg.get("min_length", 10),
        )
        user_prompt = COMMENT_USER.format(
            title=video_info.get("title", ""),
            author=video_info.get("author", ""),
            top_comments=video_info.get("top_comments", "(无)"),
            related_titles=video_info.get("related_titles", "(无)"),
        )

        raw = self.provider.chat(system_prompt, user_prompt)
        logger.info(f"[AI] 原始回复: {raw[:200] if raw else 'None'}")
        if not raw:
            return None

        text = self._clean_comment(raw)
        logger.info(f"[AI] 清洗后: {text[:100] if text else 'None'}")
        if not text:
            logger.warning(f"[AI] 评论清洗后为空，原始内容: {raw[:80]}")
            return None

        max_len = self._comment_cfg.get("max_length", 100)
        min_len = self._comment_cfg.get("min_length", 10)
        if len(text) > max_len:
            text = text[:max_len]
        if len(text) < min_len:
            logger.warning(f"[AI] 评论过短({len(text)}<{min_len})，仍然使用: {text}")

        return text

    def check_video_relevance(self, video_info: dict) -> tuple[bool, str]:
        if not self.is_filter_enabled():
            return True, ""

        sensitivity = self._filter_cfg.get("sensitivity", 50)
        system_prompt = FILTER_SYSTEM.format(
            criteria=self._filter_cfg.get("criteria", ""),
            sensitivity=sensitivity,
            sensitivity_hint=get_sensitivity_hint(sensitivity),
        )
        user_prompt = FILTER_USER.format(
            title=video_info.get("title", ""),
            author=video_info.get("author", ""),
            views=video_info.get("views", ""),
            date=video_info.get("date", ""),
            top_comments=video_info.get("top_comments", "(无)"),
            related_titles=video_info.get("related_titles", "(无)"),
        )

        raw = self.provider.chat(system_prompt, user_prompt)
        if not raw:
            return True, "AI 调用失败，默认保留"

        try:
            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(cleaned)
            keep = bool(data.get("keep", True))
            reason = str(data.get("reason", ""))
            logger.debug(f"[AI筛选] 敏感度={sensitivity} keep={keep} reason={reason}")
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
