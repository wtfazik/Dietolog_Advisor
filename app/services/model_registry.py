from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.enums import AIRoute
from app.repositories.admin import AdminRepository


logger = logging.getLogger(__name__)


class ModelRegistryService:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.repository = AdminRepository()

    async def seed_defaults(self, session) -> None:
        exists = await session.execute(text("select to_regclass('public.model_registry')"))
        if exists.scalar_one_or_none() is None:
            logger.warning(
                "Skipping model registry seeding because table 'model_registry' is absent"
            )
            return

        for provider in ("openrouter", "groq", "hyperbolic"):
            for route in AIRoute:
                models = list(getattr(self.settings, f"{provider}_{route.value}_models"))
                for priority, model_name in enumerate(models):
                    try:
                        await self.repository.upsert_model_registry_entry(
                            session=session,
                            provider=provider,
                            route=route,
                            model_name=model_name,
                            priority=priority,
                            is_active=True,
                        )
                    except SQLAlchemyError:
                        logger.exception("Model registry seeding failed")
                        return
