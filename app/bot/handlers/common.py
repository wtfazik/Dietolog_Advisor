from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import access_request_keyboard, disclaimer_keyboard, main_menu_keyboard
from app.config import get_settings
from app.db.enums import UserStatus
from app.db.session import SessionLocal
from app.i18n import normalize_locale, t
from app.repositories.users import UserRepository
from app.services.access import AccessService


router = Router()


async def get_user_and_locale(message_or_callback) -> tuple[object, str]:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message_or_callback.from_user)
        await session.commit()
        locale = (
            user.preferences.preferred_language
            if getattr(user, "preferences", None)
            else normalize_locale(user.telegram_language_code)
        )
        return user, locale


@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        await session.commit()
        locale = (
            user.preferences.preferred_language
            if user.preferences is not None
            else normalize_locale(user.telegram_language_code)
        )

        if user.status == UserStatus.PENDING and user.role.value != "superadmin":
            pending = await UserRepository().get_pending_access_request_for_user(session, user.id)
            text = t(locale, "start_pending") if pending else t(locale, "start_access_required")
            await message.answer(text, reply_markup=access_request_keyboard(locale))
            return

        if user.status in {UserStatus.REJECTED, UserStatus.BLOCKED}:
            await message.answer(t(locale, "not_approved"))
            return

        if user.consents is None or user.consents.disclaimer_accepted_at is None:
            await message.answer(t(locale, "disclaimer"), reply_markup=disclaimer_keyboard(locale))
            return

        if user.profile is None or user.preferences is None:
            from app.bot.handlers.onboarding import start_onboarding

            await start_onboarding(message, state, user, locale)
            return

        await message.answer(
            t(locale, "menu_title"),
            reply_markup=main_menu_keyboard(locale, is_admin=access_service.is_superadmin(user)),
        )


@router.callback_query(F.data == "access:request")
async def submit_access_request(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences is not None
            else normalize_locale(user.telegram_language_code)
        )
        request, created = await access_service.submit_access_request(session, user)
        await session.commit()

        if created and settings.superadmin_telegram_id:
            from app.bot.keyboards import approval_keyboard

            try:
                await callback.bot.send_message(
                    settings.superadmin_telegram_id,
                    t(
                        "ru",
                        "access_request_admin_notice",
                        name=(user.first_name or user.username or str(user.telegram_user_id)),
                        telegram_id=user.telegram_user_id,
                        username=user.username or "-",
                    ),
                    reply_markup=approval_keyboard(request.id),
                )
            except Exception:
                pass

        await callback.message.answer(
            t(locale, "access_request_received") if created else t(locale, "access_request_already_pending")
        )
        await callback.answer()
