from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import admin, common, meals, menu, onboarding, reminders
from app.config import get_settings
from app.db.session import SessionLocal
from app.logging import configure_logging
from app.services.model_registry import ModelRegistryService
from app.services.reminders import ReminderService


logger = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(common.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(onboarding.router)
    dispatcher.include_router(reminders.router)
    dispatcher.include_router(menu.router)
    dispatcher.include_router(meals.router)
    return dispatcher


async def main() -> None:
    configure_logging()
    settings = get_settings()
    if settings.app_env.lower() == "production":
        raise RuntimeError("Production deployment must use FastAPI webhook mode via app.main")
    settings.require("telegram_bot_token", "superadmin_telegram_id")

    async with SessionLocal() as session:
        await ModelRegistryService(settings).seed_defaults(session)
        await session.commit()

    bot = Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = build_dispatcher()
    reminder_service = ReminderService(settings.reminder_poll_interval_seconds)
    reminder_task = asyncio.create_task(reminder_service.run_loop(bot))

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dispatcher.start_polling(bot)
    finally:
        reminder_service._stopped.set()
        reminder_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
