from __future__ import annotations

from app.db.enums import AIRoute
from app.repositories.admin import AdminRepository


class ModelRegistryService:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.repository = AdminRepository()

    async def seed_defaults(self, session) -> None:
        for provider in ("openrouter", "groq", "hyperbolic"):
            for route in AIRoute:
                models = list(getattr(self.settings, f"{provider}_{route.value}_models"))
                for priority, model_name in enumerate(models):
                    await self.repository.upsert_model_registry_entry(
                        session=session,
                        provider=provider,
                        route=route,
                        model_name=model_name,
                        priority=priority,
                        is_active=True,
                    )
