from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.db.enums import ChatCategory, ChatDirection, MealEntryStatus
from app.db.models import (
    ChatMessage,
    MealAnalysisResult,
    MealClarification,
    MealEntry,
    MealPlan,
    MealPlanItem,
)


class MealRepository:
    async def create_meal_entry(
        self,
        session,
        user_id: int,
        initial_vision_summary: dict | None,
    ) -> MealEntry:
        meal_entry = MealEntry(user_id=user_id, initial_vision_summary=initial_vision_summary)
        session.add(meal_entry)
        await session.flush()
        return meal_entry

    async def get_meal_entry(self, session, meal_entry_id: int) -> MealEntry | None:
        result = await session.execute(
            select(MealEntry)
            .options(selectinload(MealEntry.clarifications), selectinload(MealEntry.analysis_result))
            .where(MealEntry.id == meal_entry_id)
        )
        return result.scalar_one_or_none()

    async def add_clarification(
        self,
        session,
        meal_entry_id: int,
        question_key: str,
        question_text: str,
        answer_text: str,
        sort_order: int,
    ) -> MealClarification:
        clarification = MealClarification(
            meal_entry_id=meal_entry_id,
            question_key=question_key,
            question_text=question_text,
            answer_text=answer_text,
            sort_order=sort_order,
        )
        session.add(clarification)
        await session.flush()
        return clarification

    async def complete_meal_analysis(
        self,
        session,
        meal_entry: MealEntry,
        payload: dict,
        provider: str,
        model_name: str,
    ) -> MealAnalysisResult:
        analysis = MealAnalysisResult(
            meal_entry_id=meal_entry.id,
            provider=provider,
            model_name=model_name,
            recognized_foods={"items": payload.get("recognized_foods", [])},
            estimated_calories=payload.get("estimated_calories"),
            protein_g=payload.get("protein_g"),
            fat_g=payload.get("fat_g"),
            carbs_g=payload.get("carbs_g"),
            confidence_note=payload.get("confidence_note") or payload.get("approximation_note"),
            goal_fit_assessment=payload.get("goal_fit_assessment"),
            improvement_advice=payload.get("improvement_advice"),
            alternative_suggestion=payload.get("alternative_suggestion"),
            structured_payload=payload,
        )
        meal_entry.status = MealEntryStatus.ANALYZED
        session.add(analysis)
        await session.flush()
        return analysis

    async def mark_meal_failed(self, session, meal_entry: MealEntry) -> None:
        meal_entry.status = MealEntryStatus.FAILED
        await session.flush()

    async def log_chat_message(
        self,
        session,
        user_id: int,
        direction: ChatDirection,
        category: ChatCategory,
        text: str,
        locale: str | None,
        related_meal_entry_id: int | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            user_id=user_id,
            related_meal_entry_id=related_meal_entry_id,
            direction=direction,
            category=category,
            locale=locale,
            message_text=text,
        )
        session.add(message)
        await session.flush()
        return message

    async def create_meal_plan(
        self,
        session,
        user_id: int,
        summary: str,
        provider: str | None,
        model_name: str | None,
        items: list[dict],
    ) -> MealPlan:
        meal_plan = MealPlan(
            user_id=user_id,
            summary=summary,
            generated_by_provider=provider,
            generated_by_model=model_name,
            generated_at=datetime.now(timezone.utc),
        )
        session.add(meal_plan)
        await session.flush()

        for index, item in enumerate(items):
            session.add(
                MealPlanItem(
                    meal_plan_id=meal_plan.id,
                    sort_order=index,
                    meal_type=item.get("meal_type", "meal"),
                    title=item.get("title", "Meal"),
                    description=item.get("description", ""),
                    calories_target=item.get("calories_target"),
                    protein_target=item.get("protein_target"),
                    fat_target=item.get("fat_target"),
                    carbs_target=item.get("carbs_target"),
                )
            )

        await session.flush()
        return meal_plan

    async def get_latest_meal_plan(self, session, user_id: int) -> MealPlan | None:
        result = await session.execute(
            select(MealPlan)
            .options(selectinload(MealPlan.items))
            .where(MealPlan.user_id == user_id)
            .order_by(MealPlan.created_at.desc())
        )
        return result.scalars().first()

    async def list_recent_meals(self, session, limit: int = 50) -> list[MealEntry]:
        result = await session.execute(
            select(MealEntry)
            .options(selectinload(MealEntry.analysis_result), selectinload(MealEntry.user))
            .order_by(MealEntry.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def get_7_day_calorie_summary(self, session, user_id: int) -> tuple[int, float]:
        result = await session.execute(
            select(
                func.count(MealAnalysisResult.id),
                func.coalesce(func.sum(MealAnalysisResult.estimated_calories), 0.0),
            )
            .join(MealEntry, MealAnalysisResult.meal_entry_id == MealEntry.id)
            .where(
                MealEntry.user_id == user_id,
                MealEntry.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
                - timedelta(days=6),
            )
        )
        count, calories = result.one()
        return int(count or 0), float(calories or 0.0)
