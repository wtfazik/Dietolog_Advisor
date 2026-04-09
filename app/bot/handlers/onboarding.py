from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.states import OnboardingState
from app.config import get_settings
from app.db.session import SessionLocal
from app.i18n import t
from app.repositories.users import UserRepository
from app.services.access import AccessService
from app.services.meal_plan import MealPlanService
from app.services.onboarding import OnboardingService
from app.integrations.ai.orchestrator import AIOrchestrator


router = Router()


async def start_onboarding(message: Message, state: FSMContext, user, locale: str) -> None:
    await state.set_state(OnboardingState.answering)
    await state.update_data(onboarding_index=0, onboarding_answers={})
    service = OnboardingService()
    first_step = service.steps()[0]
    await message.answer(f"{t(locale, 'onboarding_intro')}\n\n{t(locale, first_step.prompt_key)}")


@router.callback_query(F.data == "onboarding:accept_disclaimer")
async def accept_disclaimer(callback: CallbackQuery, state: FSMContext) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, callback.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences is not None
            else (user.telegram_language_code or settings.default_locale)
        )
        await UserRepository().upsert_consents(session, user.id, disclaimer_accepted=True, privacy_accepted=True)
        await session.commit()
        await callback.message.answer(t(locale, "disclaimer_accepted"))
        await callback.answer()

        reloaded = await UserRepository().get_by_id(session, user.id)
        await start_onboarding(callback.message, state, reloaded, locale)


@router.message(OnboardingState.answering)
async def onboarding_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    service = OnboardingService()
    index = data.get("onboarding_index", 0)
    answers = dict(data.get("onboarding_answers", {}))
    settings = get_settings()
    access_service = AccessService(settings)

    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences is not None
            else (user.telegram_language_code or settings.default_locale)
        )

        step = service.steps()[index]
        try:
            answers[step.key] = service.validate_answer(step, message.text or "")
        except Exception:
            await message.answer(t(locale, "input_invalid"))
            return

        next_index = index + 1
        if next_index >= len(service.steps()):
            await service.persist_answers(session, user.id, answers)
            user = await UserRepository().get_by_id(session, user.id)
            await MealPlanService(AIOrchestrator()).generate_starter_plan(session, user)
            await session.commit()
            await state.clear()
            await message.answer(
                t(locale, "onboarding_complete"),
                reply_markup=main_menu_keyboard(locale, is_admin=access_service.is_superadmin(user)),
            )
            return

        await state.update_data(onboarding_index=next_index, onboarding_answers=answers)
        await session.commit()
        await message.answer(t(locale, service.steps()[next_index].prompt_key))
