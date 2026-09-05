"""An ``LLMClient`` backed by OpenRouter. One client per call — no module state,
so a long-lived worker never leaks one tenant's key/config into the next."""

from __future__ import annotations


class OpenRouterLLM:
    def __init__(self, api_key: str, model: str, *, timeout: float = 60.0):
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def complete(self, prompt: str, *, temperature: float = 0.0) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self._api_key,
            timeout=self._timeout,
        )
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""
