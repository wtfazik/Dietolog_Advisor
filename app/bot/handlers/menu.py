from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards import admin_panel_keyboard, delete_confirm_keyboard, delete_keyboard, main_menu_keyboard, reminders_keyboard
from app.bot.states import ReminderState
from app.config import get_settings
from app.db.enums import DeletionScope, ReminderType
from app.db.session import SessionLocal
from app.i18n import normalize_locale, t
from app.integrations.ai.orchestrator import AIOrchestrator
from app.repositories.meals import MealRepository
from app.repositories.users import UserRepository
from app.services.access import AccessService
from app.services.deletion import DeletionService
from app.services.meal_plan import MealPlanService
from app.services.reminders import ReminderService
from app.services.reports import ReportService


router = Router()


@router.callback_query(F.data == "menu:meal_plan")
async def show_meal_plan(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        plan = await MealRepository().get_latest_meal_plan(session, user.id)
        if plan is None and user.profile is not None:
            plan = await MealPlanService(AIOrchestrator()).generate_starter_plan(session, user)
            plan = await MealRepository().get_latest_meal_plan(session, user.id)
            await session.commit()
        if plan is None:
            await callback.message.answer(t(locale, "no_meal_plan"))
            await callback.answer()
            return

        items = "\n".join(f"- {item.meal_type}: {item.title}. {item.description}" for item in plan.items)
        await callback.message.answer(t(locale, "meal_plan_title", summary=plan.summary, items=items))
        await callback.answer()


@router.callback_query(F.data == "menu:reports")
async def show_report(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        report = await ReportService().build_weekly_report(session, user)
        await callback.message.answer(f"{t(locale, 'report_ready')}\n\n{report}")
        await callback.answer()


@router.callback_query(F.data == "menu:profile")
async def show_profile(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        if user.profile is None or user.preferences is None:
            await callback.message.answer(t(locale, "not_approved"))
            await callback.answer()
            return
        await callback.message.answer(
            t(
                locale,
                "profile_summary",
                name=user.profile.full_name,
                age=user.profile.age,
                sex=user.profile.sex,
                height=user.profile.height_cm,
                weight=user.profile.weight_kg,
                goal=user.profile.goal,
                activity=user.profile.activity_level,
                language=user.preferences.preferred_language,
            )
        )
        await callback.answer()


@router.callback_query(F.data == "menu:reminders")
async def show_reminders(callback: CallbackQuery) -> None:
    locale = normalize_locale(callback.from_user.language_code)
    await callback.message.answer(t(locale, "reminders_intro"), reply_markup=reminders_keyboard(locale))
    await callback.answer()


@router.callback_query(F.data == "menu:delete")
async def show_delete_options(callback: CallbackQuery) -> None:
    locale = normalize_locale(callback.from_user.language_code)
    await callback.message.answer(t(locale, "delete_intro"), reply_markup=delete_keyboard(locale))
    await callback.answer()


@router.callback_query(F.data.startswith("delete:"))
async def handle_delete(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    parts = callback.data.split(":")
    locale = normalize_locale(callback.from_user.language_code)
    if len(parts) == 2:
        scope = parts[1]
        await callback.message.answer(t(locale, "delete_intro"), reply_markup=delete_confirm_keyboard(locale, scope))
        await callback.answer()
        return

    scope_value = parts[2]
    scope = DeletionScope(scope_value)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        await DeletionService().request_and_process(session, user.id, scope)
        await session.commit()
        await callback.message.answer(t(locale, "delete_done"))
        await callback.answer()


@router.callback_query(F.data == "menu:restart_onboarding")
async def restart_onboarding(callback: CallbackQuery, state: FSMContext) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        from app.bot.handlers.onboarding import start_onboarding

        await start_onboarding(callback.message, state, user, locale)
        await callback.answer()


@router.callback_query(F.data == "menu:admin")
async def show_admin_menu(callback: CallbackQuery) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        if not access_service.is_superadmin(user):
            await callback.message.answer(t(locale, "only_superadmin"))
            await callback.answer()
            return
        keyboard = None
        if settings.app_base_url.startswith("http"):
            keyboard = admin_panel_keyboard(locale, f"{settings.app_base_url.rstrip('/')}/admin")
        await callback.message.answer(t(locale, "admin_title"), reply_markup=keyboard)
        await callback.answer()


@router.callback_query(F.data.startswith("reminder:set:"))
async def set_reminder_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    reminder_type = callback.data.split(":")[-1]
    locale = normalize_locale(callback.from_user.language_code)
    await state.set_state(ReminderState.waiting_time)
    await state.update_data(reminder_type=reminder_type)
    await callback.message.answer(t(locale, "reminder_ask_time"))
    await callback.answer()


@router.callback_query(F.data.startswith("reminder:disable:"))
async def disable_reminder(callback: CallbackQuery) -> None:
    reminder_type = ReminderType(callback.data.split(":")[-1])
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = user.preferences.preferred_language if user.preferences else normalize_locale(user.telegram_language_code)
        await ReminderService(settings.reminder_poll_interval_seconds).disable_reminder(session, user.id, reminder_type)
        await session.commit()
        await callback.message.answer(t(locale, "reminder_disabled"))
        await callback.answer()
