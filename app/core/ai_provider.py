import time
import os
import json
from openai import OpenAI
from utils.logger import get_logger

logger = get_logger()


class AIProvider:

    def __init__(self, config: dict):
        ai_cfg = config.get("ai", {})
        self.client = OpenAI(
            base_url=ai_cfg.get("base_url", "https://api.deepseek.com/v1"),
            api_key=ai_cfg.get("api_key", ""),
            timeout=ai_cfg.get("timeout", 30),
        )
        self.model = ai_cfg.get("model", "deepseek-chat")
        self.max_retries = ai_cfg.get("max_retries", 2)

    def _debug_log(self, payload: dict) -> None:
        """写入本次调试会话的 AI 调用日志（不包含密钥）。"""
        try:
            payload.setdefault("sessionId", "829736")
            payload.setdefault("timestamp", int(time.time() * 1000))
            log_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "debug-829736.log"))
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # 调试日志失败不影响主流程
            pass

    def chat(self, system_prompt: str, user_prompt: str) -> str | None:
        # #region agent log
        self._debug_log({
            "location": "ai_provider.py:chat:entry",
            "message": "AI chat request",
            "hypothesisId": "AI1",
            "data": {
                "model": self.model,
                "system_preview": system_prompt[:120],
                "user_preview": user_prompt[:120],
            },
        })
        # #endregion

        for attempt in range(1, self.max_retries + 2):
            try:
                start = time.time()
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.8,
                    max_tokens=256,
                )
                elapsed = time.time() - start
                content = resp.choices[0].message.content.strip() if resp.choices else None
                usage = resp.usage
                logger.info(
                    f"[AI] 耗时 {elapsed:.1f}s | "
                    f"tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}"
                    if usage else f"[AI] 耗时 {elapsed:.1f}s"
                )
                # #region agent log
                self._debug_log({
                    "location": "ai_provider.py:chat:success",
                    "message": "AI chat response",
                    "hypothesisId": "AI2",
                    "data": {
                        "elapsed_sec": round(elapsed, 3),
                        "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                        "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
                        "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
                        "content_preview": (content or "")[:200],
                        "attempt": attempt,
                    },
                })
                # #endregion
                return content
            except Exception as e:
                logger.warning(f"[AI] 调用失败 (第{attempt}次): {e}")
                # #region agent log
                self._debug_log({
                    "location": "ai_provider.py:chat:error",
                    "message": "AI chat error",
                    "hypothesisId": "AI3",
                    "data": {
                        "attempt": attempt,
                        "error": str(e),
                        "model": self.model,
                    },
                })
                # #endregion
                if attempt > self.max_retries:
                    logger.error("[AI] 已达最大重试次数，放弃本次调用")
                    return None
                time.sleep(1.0 * attempt)
        return None
