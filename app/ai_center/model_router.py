from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from utils.logger import get_logger

logger = get_logger()


class ProviderConfig(BaseModel):
    base_url: str = "https://api.deepseek.com/v1"
    api_key: str = ""
    model: str = "deepseek-chat"
    timeout: int = 30
    max_retries: int = 2


class ModelRoute(BaseModel):
    primary_model: str
    fallback_model: Optional[str] = None
    timeout: int = 30
    max_retries: int = 2


class ModelRouterConfig(BaseModel):
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)
    routes: Dict[str, ModelRoute] = Field(default_factory=dict)


class CrossValidationResult(BaseModel):
    agreed: bool = False
    results: List[str] = Field(default_factory=list)
    details: str = ""


class AsyncAIProvider:
    """Async wrapper around the OpenAI-compatible API (mirrors core.ai_provider)."""

    def __init__(self, config: ProviderConfig) -> None:
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=config.timeout,
        )
        self.model = config.model
        self.max_retries = config.max_retries

    async def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 4096,
    ) -> str | None:
        for attempt in range(1, self.max_retries + 2):
            try:
                start = time.time()
                resp = await self.client.chat.completions.create(
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
                    f"[ModelRouter] {self.model} {elapsed:.1f}s "
                    + (
                        f"tokens: {usage.prompt_tokens}+{usage.completion_tokens}={usage.total_tokens}"
                        if usage
                        else ""
                    )
                )
                return content
            except Exception as e:
                logger.warning(f"[ModelRouter] {self.model} attempt {attempt} failed: {e}")
                if attempt > self.max_retries:
                    return None
                await asyncio.sleep(1.0 * attempt)
        return None


class ModelRouter:
    """Routes AI calls to different models based on task type, with fallback."""

    def __init__(self, config: ModelRouterConfig | None = None) -> None:
        self._config = config or ModelRouterConfig()
        self._providers: Dict[str, AsyncAIProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        for name, pcfg in self._config.providers.items():
            self._providers[name] = AsyncAIProvider(pcfg)

    def update_config(self, config: ModelRouterConfig) -> None:
        self._config = config
        self._providers.clear()
        self._init_providers()

    async def call(
        self,
        task_type: str,
        system_prompt: str,
        user_prompt: str,
        fallback: bool = True,
        temperature: float = 0.8,
        max_tokens: int = 1024,
    ) -> str | None:
        route = self._config.routes.get(task_type)
        if route is None:
            # No specific route — try the first available provider
            if self._providers:
                provider = next(iter(self._providers.values()))
                return await provider.chat(system_prompt, user_prompt, temperature, max_tokens)
            return None

        primary = self._providers.get(route.primary_model)
        if primary:
            result = await primary.chat(system_prompt, user_prompt, temperature, max_tokens)
            if result is not None:
                return result

        if fallback and route.fallback_model:
            fb = self._providers.get(route.fallback_model)
            if fb:
                logger.info(f"[ModelRouter] Falling back to {route.fallback_model} for {task_type}")
                return await fb.chat(system_prompt, user_prompt, temperature, max_tokens)

        return None

    async def cross_validate(
        self,
        task_type: str,
        prompt: str,
        models: List[str],
        system_prompt: str = "You are a validator.",
        strategy: str = "majority",
    ) -> CrossValidationResult:
        """Send the same prompt to multiple models and compare results."""
        providers = [self._providers[m] for m in models if m in self._providers]
        if not providers:
            return CrossValidationResult(details="No providers found")

        raw_results = await asyncio.gather(
            *[p.chat(system_prompt, prompt) for p in providers],
            return_exceptions=True,
        )
        texts = [r if isinstance(r, str) else str(r) for r in raw_results]

        if strategy == "consensus":
            agreed = len(set(texts)) == 1
        else:  # majority
            from collections import Counter
            counts = Counter(texts)
            most_common = counts.most_common(1)[0]
            agreed = most_common[1] > len(texts) // 2

        return CrossValidationResult(
            agreed=agreed,
            results=texts,
            details=f"strategy={strategy}, unique_answers={len(set(texts))}",
        )

    def get_available_models(self) -> List[str]:
        return list(self._providers.keys())

    def get_routes(self) -> Dict[str, ModelRoute]:
        return dict(self._config.routes)
