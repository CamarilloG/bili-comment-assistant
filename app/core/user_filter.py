"""Two-stage user filter: regex pre-filter then optional AI analysis."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger()

DM_FILTER_SYSTEM = """你是一个用户意向分析助手。根据用户在B站视频评论区的发言，判断该用户是否符合筛选条件。

筛选条件：{criteria}

请根据评论内容分析用户意图，返回 JSON 格式：
{{"match": true/false, "reason": "简短理由"}}

只返回 JSON，不要其他内容。"""

DM_FILTER_USER = """用户名: {uname}
评论内容: {content}"""


def regex_filter(
    comments: List[Dict[str, str]],
    patterns: List[str],
) -> List[Dict[str, str]]:
    """Filter comments by regex patterns. Returns comments matching ANY pattern."""
    if not patterns:
        return list(comments)

    compiled = []
    for p in patterns:
        try:
            compiled.append(re.compile(p, re.IGNORECASE))
        except re.error as e:
            logger.warning(f"[UserFilter] 正则表达式编译失败: {p!r} -> {e}")

    if not compiled:
        return list(comments)

    matched = []
    for c in comments:
        text = c.get("content", "")
        if any(r.search(text) for r in compiled):
            matched.append(c)

    logger.info(f"[UserFilter] 正则筛选: {len(comments)} -> {len(matched)} (命中 {len(matched)})")
    return matched


def ai_filter(
    comments: List[Dict[str, str]],
    criteria: str,
    ai_manager,
    max_batch: Optional[int] = None,
) -> List[Dict[str, str]]:
    """Use AI to evaluate user intent from comment text, one call per comment.

    Args:
        comments: list of {uid, uname, content}
        criteria: natural language description of the filtering criteria
        ai_manager: AIManager instance (must have .provider attribute)
    """
    if not ai_manager or not ai_manager.provider:
        logger.warning("[UserFilter] AI provider 不可用，跳过 AI 筛选")
        return list(comments)

    if not criteria.strip():
        return list(comments)

    system_prompt = DM_FILTER_SYSTEM.format(criteria=criteria)
    matched = []

    batch = comments
    if max_batch is not None:
        batch = comments[:max(0, max_batch)]

    for c in batch:
        try:
            user_prompt = DM_FILTER_USER.format(
                uname=c.get("uname", ""),
                content=c.get("content", ""),
            )
            raw = ai_manager.provider.chat(system_prompt, user_prompt)
            if not raw:
                matched.append(c)
                continue

            cleaned = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(cleaned)
            if data.get("match", False):
                logger.debug(f"[UserFilter/AI] 命中: uid={c.get('uid')} reason={data.get('reason', '')}")
                matched.append(c)
            else:
                logger.debug(f"[UserFilter/AI] 排除: uid={c.get('uid')} reason={data.get('reason', '')}")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[UserFilter/AI] 解析失败: {e}，默认保留")
            matched.append(c)
        except Exception as e:
            logger.warning(f"[UserFilter/AI] 调用异常: {e}，默认保留")
            matched.append(c)

    logger.info(f"[UserFilter] AI 筛选: {len(comments)} -> {len(matched)}")
    return matched


def filter_users(
    comments: List[Dict[str, str]],
    regex_patterns: Optional[List[str]] = None,
    use_ai: bool = False,
    ai_criteria: str = "",
    ai_manager=None,
) -> List[Dict[str, str]]:
    """Run the full two-stage filter pipeline.

    Stage 1: regex_patterns (fast, reduces candidate pool)
    Stage 2: AI analysis (slower, applied to stage-1 survivors only)
    """
    result = list(comments)

    if regex_patterns:
        result = regex_filter(result, regex_patterns)

    if use_ai and ai_criteria and ai_manager:
        result = ai_filter(result, ai_criteria, ai_manager)

    logger.info(f"[UserFilter] 最终结果: {len(comments)} -> {len(result)}")
    return result
