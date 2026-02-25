import json
import time
import os
from datetime import datetime
from openai import OpenAI
from utils.logger import get_logger
from core.crypto import decrypt_api_key

_DEFAULT_ENCRYPTED_KEY = "EQJBDUwADlxbXVpHGANCRwsXQgNWQUtDCFcPXV4fWglcWVI="

logger = get_logger()


def _get_log_dir():
    dir_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


class AIProvider:

    def __init__(self, config: dict, stop_event=None):
        ai_cfg = config.get("ai", {})
        api_key = ai_cfg.get("api_key", "")
        if not api_key:
            api_key = _DEFAULT_ENCRYPTED_KEY
        self.client = OpenAI(
            base_url=ai_cfg.get("base_url", "https://api.deepseek.com/v1"),
            api_key=decrypt_api_key(api_key),
            timeout=ai_cfg.get("timeout", 30),
        )
        self.model = "deepseek-chat"
        self.max_retries = ai_cfg.get("max_retries", 2)
        self.stop_event = stop_event

    def _is_reasoning_model(self) -> bool:
        """判断是否为推理模型"""
        return "reasoner" in self.model.lower()

    def _extract_content(self, message) -> str | None:
        """提取消息内容，支持推理模型和对话模型"""
        # 对话模型回复在 content 字段
        content = getattr(message, 'content', None)
        if content and content.strip():
            return content.strip()
        
        # 推理模型可能没有 content，只有 reasoning_content（不应该发生，但做兼容）
        if self._is_reasoning_model():
            reasoning = getattr(message, 'reasoning_content', None)
            if reasoning:
                return reasoning.strip()
        
        return content

    def chat(self, system_prompt: str, user_prompt: str) -> str | None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(_get_log_dir(), f"ai_request_{timestamp}.json")
        
        request_data = {
            "timestamp": timestamp,
            "model": self.model,
            "base_url": str(self.client.base_url),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "temperature": 0.8,
            "max_tokens": 256,
        }
        
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(request_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[AI] 请求日志已保存: {log_file}")
        
        for attempt in range(1, self.max_retries + 2):
            if self.stop_event and self.stop_event.is_set():
                logger.info("[AI] 收到停止信号，终止调用")
                return None
                
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
                usage = resp.usage
                logger.info(
                    f"[AI] 耗时 {elapsed:.1f}s | "
                    f"tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}"
                    if usage else f"[AI] 耗时 {elapsed:.1f}s"
                )
                
                response_data = {
                    "attempt": attempt,
                    "elapsed_seconds": elapsed,
                    "usage": {
                        "prompt_tokens": usage.prompt_tokens if usage else None,
                        "completion_tokens": usage.completion_tokens if usage else None,
                        "total_tokens": usage.total_tokens if usage else None,
                    },
                    "raw_response": str(resp),
                    "choices": [],
                }
                
                if not resp.choices:
                    logger.warning("[AI] 响应中没有 choices")
                    with open(log_file, "w", encoding="utf-8") as f:
                        json.dump({**request_data, **response_data}, f, ensure_ascii=False, indent=2)
                    return None
                    
                msg = resp.choices[0].message
                content = self._extract_content(msg)
                
                response_data["choices"].append({
                    "message": {
                        "role": msg.role,
                        "content": getattr(msg, 'content', None),
                        "reasoning_content": getattr(msg, 'reasoning_content', None),
                    },
                    "finish_reason": resp.choices[0].finish_reason,
                })
                
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump({**request_data, **response_data}, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[AI] 响应日志已保存: {log_file}")
                
                if content is None:
                    logger.warning(f"[AI] message.content 为 None，reason: {msg}")
                    return None
                
                if not content.strip():
                    logger.warning(f"[AI] message.content 为空字符串，原始响应: {msg}")
                    return None
                    
                return content.strip()
            except Exception as e:
                logger.warning(f"[AI] 调用失败 (第{attempt}次): {e}")
                with open(log_file, "w", encoding="utf-8") as f:
                    json.dump({**request_data, "error": str(e)}, f, ensure_ascii=False, indent=2)
                if attempt > self.max_retries:
                    logger.error("[AI] 已达最大重试次数，放弃本次调用")
                    return None
                time.sleep(1.0 * attempt)
        return None
