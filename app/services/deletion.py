from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.db.enums import DeletionScope, DeletionStatus
from app.db.models import (
    AccessRequest,
    ChatMessage,
    DeletionRequest,
    MealAnalysisResult,
    MealClarification,
    MealEntry,
    MealPlan,
    MealPlanItem,
    NotificationLog,
    Reminder,
    User,
    UserBlock,
    UserConsent,
    UserPreference,
    UserProfile,
)


class DeletionService:
    async def request_and_process(self, session, user_id: int, scope: DeletionScope) -> None:
        request = DeletionRequest(user_id=user_id, scope=scope)
        session.add(request)
        await session.flush()

        if scope == DeletionScope.HISTORY:
            await self._delete_history(session, user_id)
        elif scope == DeletionScope.PROFILE_AND_HISTORY:
            await self._delete_history(session, user_id)
            await session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
            await session.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
            await session.execute(delete(UserConsent).where(UserConsent.user_id == user_id))
            await session.execute(delete(Reminder).where(Reminder.user_id == user_id))
        elif scope == DeletionScope.FULL_ACCOUNT:
            await self._delete_history(session, user_id)
            await session.execute(delete(UserProfile).where(UserProfile.user_id == user_id))
            await session.execute(delete(UserPreference).where(UserPreference.user_id == user_id))
            await session.execute(delete(UserConsent).where(UserConsent.user_id == user_id))
            await session.execute(delete(Reminder).where(Reminder.user_id == user_id))
            await session.execute(delete(AccessRequest).where(AccessRequest.user_id == user_id))
            await session.execute(delete(UserBlock).where(UserBlock.user_id == user_id))
            await session.execute(delete(DeletionRequest).where(DeletionRequest.user_id == user_id, DeletionRequest.id != request.id))
            await session.execute(delete(User).where(User.id == user_id))

        request.status = DeletionStatus.COMPLETED
        request.processed_at = datetime.now(timezone.utc)
        await session.flush()

    async def _delete_history(self, session, user_id: int) -> None:
        meal_entry_result = await session.execute(select(MealEntry.id).where(MealEntry.user_id == user_id))
        meal_entry_ids = [row[0] for row in meal_entry_result.all()]
        if meal_entry_ids:
            await session.execute(delete(MealClarification).where(MealClarification.meal_entry_id.in_(meal_entry_ids)))
            await session.execute(delete(MealAnalysisResult).where(MealAnalysisResult.meal_entry_id.in_(meal_entry_ids)))
            await session.execute(delete(MealEntry).where(MealEntry.id.in_(meal_entry_ids)))

        meal_plan_result = await session.execute(select(MealPlan.id).where(MealPlan.user_id == user_id))
        meal_plan_ids = [row[0] for row in meal_plan_result.all()]
        if meal_plan_ids:
            await session.execute(delete(MealPlanItem).where(MealPlanItem.meal_plan_id.in_(meal_plan_ids)))
            await session.execute(delete(MealPlan).where(MealPlan.id.in_(meal_plan_ids)))

        await session.execute(delete(ChatMessage).where(ChatMessage.user_id == user_id))
        await session.execute(delete(NotificationLog).where(NotificationLog.user_id == user_id))
