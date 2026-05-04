from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.config import get_settings
from app.db.session import SessionLocal
from app.i18n import normalize_locale, t
from app.services.access import AccessService


router = Router()


@router.callback_query(F.data.startswith("admin:approve:"))
async def approve_request(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    request_id = int(callback.data.split(":")[-1])
    async with SessionLocal() as session:
        access_request = await access_service.approve_request(session, request_id, None)
        if access_request is None:
            await callback.answer()
            return
        await session.commit()
        locale = normalize_locale(access_request.user.telegram_language_code)
        await callback.bot.send_message(
            access_request.user.telegram_user_id,
            t(locale, "access_request_approved_user"),
        )
        await callback.message.answer(t("ru", "approval_done"))
        await callback.answer()


@router.callback_query(F.data.startswith("admin:reject:"))
async def reject_request(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    request_id = int(callback.data.split(":")[-1])
    async with SessionLocal() as session:
        access_request = await access_service.reject_request(session, request_id, None, None)
        if access_request is None:
            await callback.answer()
            return
        await session.commit()
        locale = normalize_locale(access_request.user.telegram_language_code)
        await callback.bot.send_message(
            access_request.user.telegram_user_id,
            t(locale, "access_request_rejected_user"),
        )
        await callback.message.answer(t("ru", "approval_done"))
        await callback.answer()
