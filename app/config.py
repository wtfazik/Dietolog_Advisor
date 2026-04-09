from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


Locale = Literal["ru", "uz_cyrl", "uz_latn"]


def _split_csv(value: str | list[str] | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item.strip() for item in value if item.strip()]
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_database_url(value: str) -> str:
    if not value.startswith("postgresql://") and not value.startswith("postgresql+"):
        return value

    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if not host.startswith("dpg-") or "." in host:
        return value

    resolved_host = f"{host}.oregon-postgres.render.com"
    auth = ""
    if parsed.username:
        auth = quote(parsed.username, safe="")
        if parsed.password:
            auth = f"{auth}:{quote(parsed.password, safe='')}"
        auth = f"{auth}@"
    port = f":{parsed.port}" if parsed.port else ""
    netloc = f"{auth}{resolved_host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Professional Dietologist"
    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    log_level: str = "INFO"
    default_locale: Locale = "ru"

    database_url: str = "sqlite+aiosqlite:///./app.db"
    database_require_ssl: bool = False

    telegram_bot_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("TELEGRAM_BOT_TOKEN", "BOT_TOKEN"),
    )
    superadmin_telegram_id: int | None = None

    openrouter_api_key: SecretStr | None = None
    groq_api_key: SecretStr | None = None
    hyperbolic_api_key: SecretStr | None = None

    admin_panel_username: str | None = None
    admin_panel_password: SecretStr | None = None

    reminder_poll_interval_seconds: int = 60
    ai_timeout_seconds: int = 45

    openrouter_vision_models: list[str] = [
        "google/gemma-4-31b-it:free",
        "nvidia/nemotron-nano-2-vl:free",
        "qwen/qwen3.6-plus:free",
    ]
    openrouter_chat_models: list[str] = [
        "qwen/qwen3.6-plus:free",
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-super:free",
        "z-ai/glm-4.5-air:free",
    ]
    openrouter_emergency_models: list[str] = [
        "stepfun/step-3.5-flash:free",
        "nvidia/nemotron-3-nano-30b-a3b:free",
        "z-ai/glm-4.5-air:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ]

    groq_vision_models: list[str] = ["meta-llama/llama-4-scout-17b-16e-instruct"]
    groq_chat_models: list[str] = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    groq_emergency_models: list[str] = ["llama-3.1-8b-instant"]

    hyperbolic_vision_models: list[str] = [
        "Qwen/Qwen2-VL-72B-Instruct",
        "meta-llama/Llama-3.2-11B-Vision-Instruct",
    ]
    hyperbolic_chat_models: list[str] = [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Meta-Llama-3.1-70B-Instruct",
    ]
    hyperbolic_emergency_models: list[str] = ["meta-llama/Meta-Llama-3.1-8B-Instruct"]

    @field_validator(
        "openrouter_vision_models",
        "openrouter_chat_models",
        "openrouter_emergency_models",
        "groq_vision_models",
        "groq_chat_models",
        "groq_emergency_models",
        "hyperbolic_vision_models",
        "hyperbolic_chat_models",
        "hyperbolic_emergency_models",
        mode="before",
    )
    @classmethod
    def split_model_lists(cls, value: str | list[str] | None) -> list[str]:
        return _split_csv(value)

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent

    @property
    def templates_dir(self) -> Path:
        return self.base_dir / "templates"

    @property
    def prompts_dir(self) -> Path:
        return self.base_dir / "prompts"

    @property
    def i18n_dir(self) -> Path:
        return self.base_dir / "i18n"

    @property
    def async_database_url(self) -> str:
        normalized = _normalize_database_url(self.database_url)
        if normalized.startswith("postgresql+asyncpg://"):
            return normalized
        if normalized.startswith("postgresql://"):
            return normalized.replace("postgresql://", "postgresql+asyncpg://", 1)
        return normalized

    @property
    def sync_database_url(self) -> str:
        normalized = _normalize_database_url(self.database_url)
        if normalized.startswith("postgresql+psycopg://"):
            return normalized
        if normalized.startswith("postgresql+asyncpg://"):
            return normalized.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
        if normalized.startswith("postgresql://"):
            return normalized.replace("postgresql://", "postgresql+psycopg://", 1)
        return normalized

    @property
    def database_host(self) -> str:
        return urlsplit(_normalize_database_url(self.database_url)).hostname or ""

    @property
    def uses_external_pooler(self) -> bool:
        parsed = urlsplit(_normalize_database_url(self.database_url))
        query = {key.lower(): value for key, value in parse_qsl(parsed.query)}
        host = parsed.hostname or ""
        return "pooler.supabase.com" in host or query.get("pgbouncer", "").lower() == "true"

    @property
    def async_connect_args(self) -> dict[str, object]:
        connect_args: dict[str, object] = {}
        if self.database_require_ssl and self.async_database_url.startswith("postgresql+"):
            connect_args["ssl"] = "require"
        if self.uses_external_pooler and self.async_database_url.startswith("postgresql+"):
            connect_args["statement_cache_size"] = 0
        return connect_args

    @property
    def sync_connect_args(self) -> dict[str, object]:
        connect_args: dict[str, object] = {}
        if self.database_require_ssl and self.sync_database_url.startswith("postgresql+"):
            connect_args["sslmode"] = "require"
        return connect_args

    def require(self, *fields: str) -> None:
        missing = []
        for field in fields:
            value = getattr(self, field)
            if value is None or value == "":
                missing.append(field)
        if missing:
            joined = ", ".join(missing)
            raise RuntimeError(f"Missing required settings: {joined}")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
