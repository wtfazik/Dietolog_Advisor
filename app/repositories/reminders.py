from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select

from app.db.enums import ReminderType
from app.db.models import NotificationLog, Reminder


class ReminderRepository:
    async def upsert_reminder(
        self,
        session,
        user_id: int,
        reminder_type: ReminderType,
        reminder_time: time,
        timezone_name: str = "UTC",
    ) -> Reminder:
        result = await session.execute(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.reminder_type == reminder_type,
            )
        )
        reminder = result.scalar_one_or_none()
        if reminder is None:
            reminder = Reminder(user_id=user_id, reminder_type=reminder_type, reminder_time=reminder_time)
            session.add(reminder)

        reminder.enabled = True
        reminder.reminder_time = reminder_time
        reminder.timezone = timezone_name
        reminder.next_run_at = self._next_run_at(reminder_time)
        await session.flush()
        return reminder

    async def disable_reminder(self, session, user_id: int, reminder_type: ReminderType) -> None:
        result = await session.execute(
            select(Reminder).where(
                Reminder.user_id == user_id,
                Reminder.reminder_type == reminder_type,
            )
        )
        reminder = result.scalar_one_or_none()
        if reminder is not None:
            reminder.enabled = False
            reminder.next_run_at = None
            await session.flush()

    async def list_user_reminders(self, session, user_id: int) -> list[Reminder]:
        result = await session.execute(
            select(Reminder)
            .where(Reminder.user_id == user_id)
            .order_by(Reminder.reminder_type.asc())
        )
        return list(result.scalars())

    async def list_due_reminders(self, session, current_time: datetime) -> list[Reminder]:
        result = await session.execute(
            select(Reminder).where(
                Reminder.enabled.is_(True),
                Reminder.next_run_at.is_not(None),
                Reminder.next_run_at <= current_time,
            )
        )
        return list(result.scalars())

    async def mark_sent(self, session, reminder: Reminder, message_text: str, status: str) -> NotificationLog:
        reminder.last_sent_at = datetime.now(timezone.utc)
        reminder.next_run_at = self._next_run_at(reminder.reminder_time)
        log_entry = NotificationLog(
            reminder_id=reminder.id,
            user_id=reminder.user_id,
            status=status,
            message_text=message_text,
            sent_at=reminder.last_sent_at,
        )
        session.add(log_entry)
        await session.flush()
        return log_entry

    def _next_run_at(self, reminder_time: time) -> datetime:
        now = datetime.now(timezone.utc)
        candidate = now.replace(
            hour=reminder_time.hour,
            minute=reminder_time.minute,
            second=0,
            microsecond=0,
        )
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
