import json
import re
import random
from core.ai_provider import AIProvider
from core.models_registry import get_model_by_id
from core.prompts import COMMENT_SYSTEM, COMMENT_USER, FILTER_SYSTEM, FILTER_USER
from utils.logger import get_logger

logger = get_logger()

# 评论策略：按标题/评论关键词粗分类型，每类对应一句注入 prompt 的推荐角度（可多条随机）
COMMENT_STRATEGY_KEYWORDS = {
    "teaching": (
        ["教学", "攻略", "萌新", "技巧", "上分", "改枪", "配装", "配置", "改法", "怎么"],
        [
            "推荐角度: 偏向教学向，可认同打法或补充一条小技巧，再自然带一句一起研究上分。",
            "推荐角度: 像老玩家看完攻略后的反应，夸一句实用或说自己也这么配，再约一起试。",
        ],
    ),
    "highlight": (
        ["1v", "高光", "秀", "传说", "对狙", "操作", "绝杀", "清图", "裸枪", "神"],
        [
            "推荐角度: 夸具体操作或武器/场面，别泛泛说「太秀了」，可顺带说缺这种队友、约排位。",
            "推荐角度: 针对标题里的名场面或武器名写一句，再自然带出找搭子/组队。",
        ],
    ),
    "funny": (
        ["演", "搞笑", "笑", "整活", "离谱", "玉玉", "红温", "演队友"],
        [
            "推荐角度: 跟着玩梗或自嘲，语气轻松，再顺手约开黑，不要正经教学口吻。",
            "推荐角度: 调侃视频里的梗或场面，像在跟楼里聊天，自然带一句凑人一起玩。",
        ],
    ),
    "loadout": (
        ["枪", "M7", "巡飞弹", "武器", "改枪", "配装", "性价比", "裸枪", "套"],
        [
            "推荐角度: 扣住武器/改法名称，说一句实用感受或想试试，再问有没有一起试这套的。",
            "推荐角度: 针对UP主这套配装或套路给一句具体反应，再自然带出组队试套路。",
        ],
    ),
}
DEFAULT_STRATEGY_HINTS = [
    "推荐角度: 根据标题和关联视频判断是教学/实战/整活，针对具体点写一句，再自然带出开黑或组队。",
]

# 风格预设：用于 prompt 的简短描述，style=random 时随机选一种
STYLE_DESCRIPTIONS = {
    "casual": "轻松娱乐，像日常唠嗑",
    "hardcore": "硬核上分党，偏技术讨论",
    "newbie_friendly": "照顾萌新，语气友好、可带一点小建议",
}

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


def _pick_comment_strategy(video_info: dict) -> str:
    """根据标题和热门评论做简单分类，返回一句注入 user prompt 的策略提示，无则返回空。"""
    title = (video_info.get("title") or "") + " " + (video_info.get("related_titles") or "")
    comments = video_info.get("top_comments") or ""
    text = (title + " " + comments).lower()
    for _cat, (keywords, hints) in COMMENT_STRATEGY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return random.choice(hints)
    return random.choice(DEFAULT_STRATEGY_HINTS)


class AIManager:

    def __init__(self, config: dict):
        self.config = config
        ai_cfg = config.get("ai", {})
        model_id = ai_cfg.get("model_id") or ""
        model_cfg = get_model_by_id(model_id) if model_id else None
        has_key = bool(model_cfg and (model_cfg.get("api_key") or "").strip())
        need_comment = ai_cfg.get("comment", {}).get("enabled", False)
        need_filter = ai_cfg.get("filter", {}).get("enabled", False) and bool(
            (ai_cfg.get("filter", {}).get("criteria") or "").strip()
        )
        if has_key and (need_comment or need_filter) and model_cfg:
            timeout = max(5, int(ai_cfg.get("timeout", 30)))
            max_retries = max(0, int(ai_cfg.get("max_retries", 2)))
            request_interval = max(0.0, float(ai_cfg.get("request_interval", 0.0)))
            retry_delay_base = max(0.5, float(ai_cfg.get("retry_delay_base", 2.0)))
            self.provider = AIProvider(
                model_cfg,
                timeout=timeout,
                max_retries=max_retries,
                request_interval=request_interval,
                retry_delay_base=retry_delay_base,
            )
        else:
            self.provider = None
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

        style_key = self._comment_cfg.get("style", "casual")
        if style_key == "random":
            style_key = random.choice(list(STYLE_DESCRIPTIONS.keys()))
        style_desc = STYLE_DESCRIPTIONS.get(style_key, STYLE_DESCRIPTIONS["casual"])
        temperature = self._comment_cfg.get("temperature")
        if temperature is None:
            temperature = 0.85
        max_tokens = self._comment_cfg.get("max_tokens", 2048)

        system_prompt = COMMENT_SYSTEM.format(
            user_intent=self._comment_cfg.get("user_intent", "") or "普通B站用户",
            style=style_desc,
            max_length=self._comment_cfg.get("max_length", 100),
            min_length=self._comment_cfg.get("min_length", 10),
        )
        strategy_hint = _pick_comment_strategy(video_info)
        user_prompt = COMMENT_USER.format(
            title=video_info.get("title", ""),
            author=video_info.get("author", ""),
            top_comments=video_info.get("top_comments", "(无)"),
            related_titles=video_info.get("related_titles", "(无)"),
            strategy_hint=strategy_hint,
        )

        raw = self.provider.chat(
            system_prompt,
            user_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            prompt_version="comment_v2",
        )
        if not raw:
            return None

        text = self._clean_comment(raw)
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
    def _clean_comment(text: str) -> str | None:
        """清洗评论：去前缀/引号、去口水句开头、过滤违规词；若命中违规则返回 None。"""
        text = text.strip().strip('"').strip("'").strip(""").strip(""")
        prefixes = ["以下是评论：", "以下是评论:", "评论：", "评论:", "评论内容：", "评论内容:"]
        for p in prefixes:
            if text.startswith(p):
                text = text[len(p):].strip()
        # 去掉无信息量的开头口水句（若去掉后过短则保留原句）
        filler_starts = ["说实话，", "不得不说，", "确实，", "真的，"]
        for f in filler_starts:
            if text.startswith(f) and len(text) > len(f) + 5:
                text = text[len(f):].strip()
        # 违规/硬广短语：命中则丢弃本条评论
        forbidden = ["加群", "福利", "拉群", "扫码", "加V", "私信", "点击链接", "进群", "联系客服"]
        for w in forbidden:
            if w in text:
                logger.warning(f"[AI] 评论含违规词「{w}」已丢弃: {text[:60]}…")
                return None
        return text if text else None
