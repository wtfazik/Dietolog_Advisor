from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import select

from app.config import get_settings
from app.db.enums import AIRoute, AIRequestStatus
from app.db.models import AIFallbackLog, AIRequestLog, ModelRegistry
from app.integrations.ai.base import AIResponse, ProviderError
from app.integrations.ai.providers import GroqProvider, HyperbolicProvider, OpenRouterProvider


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AttemptRecord:
    provider: str
    model: str
    reason: str | None = None


class AIOrchestrator:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.providers = {
            "openrouter": OpenRouterProvider(
                api_key=settings.openrouter_api_key.get_secret_value()
                if settings.openrouter_api_key
                else None,
                app_url=settings.app_base_url,
            ),
            "groq": GroqProvider(
                api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
            ),
            "hyperbolic": HyperbolicProvider(
                api_key=settings.hyperbolic_api_key.get_secret_value() if settings.hyperbolic_api_key else None
            ),
        }
        self.provider_order = ["openrouter", "groq", "hyperbolic"]

    async def request(
        self,
        route: AIRoute,
        messages: list[dict],
        session=None,
        user_id: int | None = None,
        meal_entry_id: int | None = None,
        prompt_name: str | None = None,
    ) -> AIResponse:
        previous_attempt: AttemptRecord | None = None
        last_error: Exception | None = None

        for provider_name in self.provider_order:
            provider = self.providers[provider_name]
            if not provider.enabled:
                continue

            models = await self._resolve_models(route=route, provider_name=provider_name, session=session)
            for model in models:
                started = perf_counter()
                try:
                    response = await provider.complete(
                        model=model,
                        messages=messages,
                        timeout_seconds=self.settings.ai_timeout_seconds,
                    )
                except ProviderError as exc:
                    latency_ms = int((perf_counter() - started) * 1000)
                    request_log = await self._log_request(
                        session=session,
                        provider=provider_name,
                        model=model,
                        route=route,
                        status=AIRequestStatus.FAILURE,
                        latency_ms=latency_ms,
                        prompt_name=prompt_name,
                        request_excerpt=self._truncate_messages(messages),
                        response_excerpt=None,
                        error_message=str(exc),
                        user_id=user_id,
                        meal_entry_id=meal_entry_id,
                    )
                    if previous_attempt is not None:
                        await self._log_fallback(
                            session,
                            request_log_id=request_log.id if request_log else None,
                            previous_attempt=previous_attempt,
                            next_attempt=AttemptRecord(provider=provider_name, model=model, reason=str(exc)),
                        )
                    previous_attempt = AttemptRecord(provider=provider_name, model=model, reason=str(exc))
                    last_error = exc
                    logger.warning("AI attempt failed provider=%s model=%s error=%s", provider_name, model, exc)
                    continue

                latency_ms = int((perf_counter() - started) * 1000)
                await self._log_request(
                    session=session,
                    provider=provider_name,
                    model=model,
                    route=route,
                    status=AIRequestStatus.SUCCESS,
                    latency_ms=latency_ms,
                    prompt_name=prompt_name,
                    request_excerpt=self._truncate_messages(messages),
                    response_excerpt=response.text[:1000],
                    error_message=None,
                    user_id=user_id,
                    meal_entry_id=meal_entry_id,
                )
                return response

        raise RuntimeError(f"All AI providers failed for route {route}. Last error: {last_error}")

    async def _resolve_models(self, route: AIRoute, provider_name: str, session=None) -> list[str]:
        if session is not None:
            result = await session.execute(
                select(ModelRegistry.model_name)
                .where(
                    ModelRegistry.provider == provider_name,
                    ModelRegistry.route == route,
                    ModelRegistry.is_active.is_(True),
                )
                .order_by(ModelRegistry.priority.asc(), ModelRegistry.id.asc())
            )
            models = list(result.scalars())
            if models:
                return models

        route_suffix = route.value
        return list(getattr(self.settings, f"{provider_name}_{route_suffix}_models"))

    async def _log_request(
        self,
        session,
        provider: str,
        model: str,
        route: AIRoute,
        status: AIRequestStatus,
        latency_ms: int,
        prompt_name: str | None,
        request_excerpt: str | None,
        response_excerpt: str | None,
        error_message: str | None,
        user_id: int | None,
        meal_entry_id: int | None,
    ):
        if session is None:
            return None
        entry = AIRequestLog(
            user_id=user_id,
            meal_entry_id=meal_entry_id,
            provider=provider,
            model_name=model,
            route=route,
            status=status,
            latency_ms=latency_ms,
            prompt_name=prompt_name,
            request_excerpt=request_excerpt,
            response_excerpt=response_excerpt,
            error_message=error_message,
        )
        session.add(entry)
        await session.flush()
        return entry

    async def _log_fallback(self, session, request_log_id: int | None, previous_attempt: AttemptRecord, next_attempt: AttemptRecord) -> None:
        if session is None:
            return
        session.add(
            AIFallbackLog(
                request_log_id=request_log_id,
                from_provider=previous_attempt.provider,
                from_model=previous_attempt.model,
                to_provider=next_attempt.provider,
                to_model=next_attempt.model,
                reason=previous_attempt.reason or next_attempt.reason or "fallback",
            )
        )
        await session.flush()

    def _truncate_messages(self, messages: list[dict]) -> str:
        rendered = []
        for message in messages:
            content = message.get("content", "")
            if isinstance(content, list):
                text_parts = [item.get("text", "") for item in content if item.get("type") == "text"]
                content = " ".join(text_parts)
            rendered.append(f"{message.get('role')}: {str(content)[:250]}")
        return "\n".join(rendered)[:1500]
