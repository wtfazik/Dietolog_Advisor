from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.runner import build_dispatcher
from app.db.session import SessionLocal
from app.services.model_registry import ModelRegistryService
from app.services.reminders import ReminderService


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class TelegramWebhookRuntime:
    bot: Bot
    dispatcher: Dispatcher
    reminder_service: ReminderService
    reminder_task: asyncio.Task
    webhook_url: str
    webhook_registered: bool


def build_webhook_url(app_base_url: str) -> str:
    return f"{app_base_url.rstrip('/')}/telegram/webhook"


async def start_telegram_runtime(settings) -> TelegramWebhookRuntime:
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
    webhook_url = build_webhook_url(settings.app_base_url)
    webhook_registered = False

    if webhook_url.startswith("https://"):
        await bot.set_webhook(
            url=webhook_url,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
        webhook_registered = True
    else:
        logger.warning(
            "Skipping webhook registration because APP_BASE_URL is not public HTTPS: %s",
            settings.app_base_url,
        )

    return TelegramWebhookRuntime(
        bot=bot,
        dispatcher=dispatcher,
        reminder_service=reminder_service,
        reminder_task=reminder_task,
        webhook_url=webhook_url,
        webhook_registered=webhook_registered,
    )


async def stop_telegram_runtime(runtime: TelegramWebhookRuntime) -> None:
    runtime.reminder_service._stopped.set()
    runtime.reminder_task.cancel()
    with suppress(asyncio.CancelledError):
        await runtime.reminder_task

    if runtime.webhook_registered:
        with suppress(Exception):
            await runtime.bot.delete_webhook(drop_pending_updates=False)

    await runtime.bot.session.close()
