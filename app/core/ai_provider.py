import time
import os
import json
from core.ai_adapters import create_client
from utils.logger import get_logger

logger = get_logger()


class AIProvider:

    def __init__(
        self,
        model_config: dict,
        timeout: int = 30,
        max_retries: int = 2,
        request_interval: float = 0.0,
        retry_delay_base: float = 2.0,
    ):
        """
        初始化 AI Provider

        Args:
            model_config: 模型配置字典
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            request_interval: 每次请求前的等待时间（秒），用于限制调用频率
            retry_delay_base: 重试延迟基数（秒），实际延迟为 base * attempt
        """
        self.client = create_client(
            base_url=model_config.get("base_url", ""),
            api_key=model_config.get("api_key", ""),
            timeout=timeout,
            api_type=model_config.get("api_type", "openai"),
        )
        self.model = model_config.get("model", "deepseek-chat")
        self.max_retries = max_retries
        self.request_interval = request_interval
        self.retry_delay_base = retry_delay_base
        self.last_request_time = 0  # 上次请求时间戳

    def _simplify_error_message(self, error: Exception) -> str:
        """简化错误信息，提取关键内容"""
        error_str = str(error)

        # 提取常见错误类型
        if "403" in error_str or "PermissionDenied" in error_str:
            if "not available in your region" in error_str:
                return "模型在当前地区不可用，请检查网络或更换模型"
            return "权限被拒绝，请检查 API Key 是否正确"

        if "401" in error_str or "Unauthorized" in error_str:
            return "API Key 无效或已过期"

        if "429" in error_str or "RateLimitError" in error_str:
            return "请求频率过高，请稍后重试"

        if "timeout" in error_str.lower() or "timed out" in error_str.lower():
            return "网络超时，请检查网络连接"

        if "connection" in error_str.lower() or "network" in error_str.lower():
            return "网络连接失败，请检查网络设置"

        if "404" in error_str:
            return "模型不存在，请检查模型名称"

        if "500" in error_str or "502" in error_str or "503" in error_str:
            return "服务器错误，请稍后重试"

        # 如果无法识别，返回简短的错误信息
        if len(error_str) > 100:
            return error_str[:100] + "..."
        return error_str

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

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        prompt_version: str | None = None,
    ) -> str | None:
        if temperature is None:
            temperature = 0.8
        if max_tokens is None:
            max_tokens = 2048

        # 调用间隔控制：确保两次请求之间有足够的间隔
        if self.request_interval > 0:
            elapsed_since_last = time.time() - self.last_request_time
            if elapsed_since_last < self.request_interval:
                wait_time = self.request_interval - elapsed_since_last
                logger.debug(f"[AI] 调用间隔控制：等待 {wait_time:.1f}s")
                time.sleep(wait_time)

        log_data = {
            "model": self.model,
            "system_preview": system_prompt[:120],
            "user_preview": user_prompt[:120],
        }
        if prompt_version is not None:
            log_data["prompt_version"] = prompt_version
        # #region agent log
        self._debug_log({
            "location": "ai_provider.py:chat:entry",
            "message": "AI chat request",
            "hypothesisId": "AI1",
            "data": log_data,
        })
        # #endregion

        for attempt in range(1, self.max_retries + 2):
            try:
                start = time.time()
                self.last_request_time = start  # 记录请求时间
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.time() - start
                content = resp.choices[0].message.content.strip() if resp.choices else None
                usage = resp.usage
                logger.info(
                    f"[AI] 耗时 {elapsed:.1f}s | "
                    f"tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}"
                    if usage else f"[AI] 耗时 {elapsed:.1f}s"
                )
                success_data = {
                    "elapsed_sec": round(elapsed, 3),
                    "prompt_tokens": getattr(usage, "prompt_tokens", None) if usage else None,
                    "completion_tokens": getattr(usage, "completion_tokens", None) if usage else None,
                    "total_tokens": getattr(usage, "total_tokens", None) if usage else None,
                    "content_preview": (content or "")[:200],
                    "attempt": attempt,
                }
                if prompt_version is not None:
                    success_data["prompt_version"] = prompt_version
                # #region agent log
                self._debug_log({
                    "location": "ai_provider.py:chat:success",
                    "message": "AI chat response",
                    "hypothesisId": "AI2",
                    "data": success_data,
                })
                # #endregion
                return content
            except Exception as e:
                # 简化错误信息，只记录关键信息
                error_msg = self._simplify_error_message(e)

                if attempt == 1:
                    # 第一次失败时简单提示
                    logger.warning(f"[AI] 调用失败，正在重试... ({error_msg})")
                elif attempt <= self.max_retries:
                    # 中间重试时不输出
                    pass
                else:
                    # 最后一次失败时输出详细原因
                    logger.error(f"[AI] 调用失败: {error_msg}")

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
                    return None
                # 使用可配置的重试延迟，支持指数退避
                retry_delay = self.retry_delay_base * attempt
                logger.debug(f"[AI] 重试延迟: {retry_delay:.1f}s")
                time.sleep(retry_delay)
        return None
