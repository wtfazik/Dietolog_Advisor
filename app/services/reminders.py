from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timezone

from aiogram import Bot

from app.db.enums import ReminderType
from app.db.session import SessionLocal
from app.repositories.reminders import ReminderRepository
from app.repositories.users import UserRepository
from app.services.reports import ReportService


logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, interval_seconds: int) -> None:
        self.interval_seconds = interval_seconds
        self.repository = ReminderRepository()
        self.users = UserRepository()
        self.reports = ReportService()
        self._task: asyncio.Task | None = None
        self._stopped = asyncio.Event()

    def parse_time(self, value: str) -> time:
        parsed = datetime.strptime(value.strip(), "%H:%M")
        return time(hour=parsed.hour, minute=parsed.minute)

    async def save_reminder(self, session, user_id: int, reminder_type: ReminderType, value: str):
        reminder_time = self.parse_time(value)
        return await self.repository.upsert_reminder(session, user_id, reminder_type, reminder_time)

    async def disable_reminder(self, session, user_id: int, reminder_type: ReminderType) -> None:
        await self.repository.disable_reminder(session, user_id, reminder_type)

    async def list_user_reminders(self, session, user_id: int):
        return await self.repository.list_user_reminders(session, user_id)

    async def run_loop(self, bot: Bot) -> None:
        while not self._stopped.is_set():
            try:
                await self.process_due_reminders(bot)
            except Exception as exc:
                logger.exception("Reminder loop failed: %s", exc)
            await asyncio.sleep(self.interval_seconds)

    async def process_due_reminders(self, bot: Bot) -> None:
        async with SessionLocal() as session:
            reminders = await self.repository.list_due_reminders(session, datetime.now(timezone.utc))
            for reminder in reminders:
                user = await self.users.get_by_id(session, reminder.user_id)
                if user is None:
                    continue
                message_text = await self._build_message(session, user, reminder.reminder_type)
                status = "sent"
                try:
                    await bot.send_message(user.telegram_user_id, message_text)
                except Exception as exc:
                    status = f"failed: {exc.__class__.__name__}"
                await self.repository.mark_sent(session, reminder, message_text, status)
            await session.commit()

    async def _build_message(self, session, user, reminder_type: ReminderType) -> str:
        if reminder_type == ReminderType.MEAL:
            return (
                "Reminder: keep your meal structured. Prioritize protein, vegetables, measured portions, and avoid untracked sauces or oils."
            )
        return await self.reports.build_weekly_report(session, user)
