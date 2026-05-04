from __future__ import annotations

from typing import Any

import httpx

from app.integrations.ai.base import AIResponse, BaseAIProvider, ProviderError


def _extract_message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "\n".join(part for part in parts if part)
    return str(content)


class OpenAICompatibleProvider(BaseAIProvider):
    provider_headers: dict[str, str] = {}

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        timeout_seconds: int,
    ) -> AIResponse:
        if not self.enabled:
            raise ProviderError(f"Provider {self.name} is not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.provider_headers,
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)

        if response.status_code >= 400:
            raise ProviderError(
                f"{self.name} request failed with status {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise ProviderError(f"Unexpected {self.name} response format") from exc

        return AIResponse(provider=self.name, model=model, text=_extract_message_text(content), raw=data)


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"

    def __init__(self, api_key: str | None, app_url: str):
        super().__init__(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        self.provider_headers = {"HTTP-Referer": app_url, "X-Title": "Professional Dietologist"}


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"

    def __init__(self, api_key: str | None):
        super().__init__(api_key=api_key, base_url="https://api.groq.com/openai/v1")


class HyperbolicProvider(OpenAICompatibleProvider):
    name = "hyperbolic"

    def __init__(self, api_key: str | None):
        super().__init__(api_key=api_key, base_url="https://api.hyperbolic.xyz/v1")
