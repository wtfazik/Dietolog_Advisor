from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ProviderError(RuntimeError):
    pass


@dataclass(slots=True)
class AIResponse:
    provider: str
    model: str
    text: str
    raw: dict[str, Any]


class BaseAIProvider:
    name: str

    def __init__(self, api_key: str | None, base_url: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)

    async def complete(
        self,
        model: str,
        messages: list[dict[str, Any]],
        timeout_seconds: int,
    ) -> AIResponse:
        raise NotImplementedError
