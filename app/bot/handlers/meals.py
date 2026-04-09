from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards import main_menu_keyboard
from app.bot.states import MealClarificationState
from app.config import get_settings
from app.db.enums import UserStatus
from app.db.session import SessionLocal
from app.i18n import normalize_locale, t
from app.integrations.ai.orchestrator import AIOrchestrator
from app.repositories.meals import MealRepository
from app.repositories.users import UserRepository
from app.services.access import AccessService
from app.services.meal_analysis import CLARIFICATION_QUESTIONS, MealAnalysisService
from app.services.nutrition_chat import NutritionChatService
from app.services.topic_guard import TopicGuardService


router = Router()


@router.callback_query(F.data == "menu:analyze_meal")
async def ask_for_photo(callback: CallbackQuery) -> None:
    locale = normalize_locale(callback.from_user.language_code)
    await callback.message.answer(t(locale, "send_meal_photo"))
    await callback.answer()


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext) -> None:
    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences
            else normalize_locale(user.telegram_language_code)
        )
        if user.status != UserStatus.APPROVED or user.profile is None:
            await message.answer(t(locale, "not_approved"))
            return

        file = await message.bot.get_file(message.photo[-1].file_id)
        photo_bytes = await message.bot.download_file(file.file_path)
        image_content = photo_bytes.read()

        service = MealAnalysisService(AIOrchestrator())
        try:
            meal_entry, vision = await service.start_photo_analysis(session, user, image_content)
        except Exception:
            await session.rollback()
            await message.answer(t(locale, "meal_analysis_failed"))
            return
        await session.commit()
        await state.set_state(MealClarificationState.answering)
        await state.update_data(meal_entry_id=meal_entry.id, clarification_index=0)
        items = (
            ", ".join(vision.recognized_items)
            if vision.recognized_items
            else "неопределенные компоненты"
        )
        await message.answer(t(locale, "meal_vision_intro", items=items))
        first_question_key = CLARIFICATION_QUESTIONS[0][1]
        await message.answer(t(locale, first_question_key))


@router.message(MealClarificationState.answering)
async def handle_clarification_answer(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    meal_entry_id = data["meal_entry_id"]
    index = data.get("clarification_index", 0)

    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences
            else normalize_locale(user.telegram_language_code)
        )

        question_key, text_key = CLARIFICATION_QUESTIONS[index]
        service = MealAnalysisService(AIOrchestrator())
        await service.save_clarification(
            session=session,
            meal_entry_id=meal_entry_id,
            question_key=question_key,
            question_text=t(locale, text_key),
            answer_text=message.text or "",
            sort_order=index,
            user_id=user.id,
            locale=locale,
        )

        next_index = index + 1
        if next_index >= len(CLARIFICATION_QUESTIONS):
            try:
                analysis = await service.finalize_analysis(session, user, meal_entry_id)
                foods = ", ".join(food.name for food in analysis.recognized_foods) or "-"
                await session.commit()
                await state.clear()
                await message.answer(
                    t(
                        locale,
                        "meal_result",
                        foods=foods,
                        calories=round(analysis.estimated_calories, 1),
                        protein=round(analysis.protein_g, 1),
                        fat=round(analysis.fat_g, 1),
                        carbs=round(analysis.carbs_g, 1),
                        goal_fit=analysis.goal_fit_assessment,
                        improve=analysis.improvement_advice,
                        alternative=analysis.alternative_suggestion or "-",
                        note=analysis.approximation_note,
                    ),
                    reply_markup=main_menu_keyboard(
                        locale, is_admin=access_service.is_superadmin(user)
                    ),
                )
            except Exception:
                await session.commit()
                await state.clear()
                await message.answer(t(locale, "meal_analysis_failed"))
            return

        await session.commit()
        await state.update_data(clarification_index=next_index)
        await message.answer(t(locale, CLARIFICATION_QUESTIONS[next_index][1]))


@router.callback_query(F.data == "menu:question")
async def question_prompt(callback: CallbackQuery) -> None:
    locale = normalize_locale(callback.from_user.language_code)
    await callback.message.answer(t(locale, "question_prompt"))
    await callback.answer()


@router.message(F.text)
async def handle_free_text(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is not None:
        return

    settings = get_settings()
    access_service = AccessService(settings)
    async with SessionLocal() as session:
        user = await access_service.get_or_create_user_from_telegram(session, message.from_user)
        user = await UserRepository().get_by_id(session, user.id)
        locale = (
            user.preferences.preferred_language
            if user.preferences
            else normalize_locale(user.telegram_language_code)
        )
        if user.status != UserStatus.APPROVED or user.profile is None:
            await message.answer(t(locale, "not_approved"))
            return

        chat_service = NutritionChatService(AIOrchestrator(), TopicGuardService(AIOrchestrator()))
        answer = await chat_service.answer_question(session, user, message.text or "", locale)
        await session.commit()
        if answer.startswith("I only provide professional guidance"):
            answer = t(locale, "question_unrelated")
        await message.answer(answer)
