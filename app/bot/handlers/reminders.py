from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.states import ReminderState
from app.config import get_settings
from app.db.enums import ReminderType
from app.db.session import SessionLocal
from app.i18n import normalize_locale, t
from app.repositories.users import UserRepository
from app.services.access import AccessService
from app.services.reminders import ReminderService


router = Router()


@router.message(ReminderState.waiting_time)
async def save_reminder_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    reminder_type = ReminderType(data["reminder_type"])
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        try:
            await ReminderService(settings.reminder_poll_interval_seconds).save_reminder(
                session, user.id, reminder_type, message.text or ""
            )
        except Exception:
            await message.answer(t(locale, "input_invalid"))
            return
        await session.commit()
        await state.clear()
        await message.answer(t(locale, "reminder_saved"))
