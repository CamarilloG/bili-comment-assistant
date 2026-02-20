import time
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

    def chat(self, system_prompt: str, user_prompt: str) -> str | None:
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
                return content
            except Exception as e:
                logger.warning(f"[AI] 调用失败 (第{attempt}次): {e}")
                if attempt > self.max_retries:
                    logger.error("[AI] 已达最大重试次数，放弃本次调用")
                    return None
                time.sleep(1.0 * attempt)
        return None
