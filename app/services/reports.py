from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.db.models import MealAnalysisResult, MealEntry
from app.services.nutrition import calculate_daily_targets


class ReportService:
    async def build_weekly_report(self, session, user) -> str:
        since = datetime.now(timezone.utc) - timedelta(days=7)
        result = await session.execute(
            select(
                func.count(MealAnalysisResult.id),
                func.coalesce(func.sum(MealAnalysisResult.estimated_calories), 0.0),
                func.coalesce(func.avg(MealAnalysisResult.estimated_calories), 0.0),
            )
            .join(MealEntry, MealAnalysisResult.meal_entry_id == MealEntry.id)
            .where(MealEntry.user_id == user.id, MealEntry.created_at >= since)
        )
        meals_count, total_calories, average_calories = result.one()
        targets = calculate_daily_targets(user.profile) if user.profile else None

        lines = [
            "Weekly nutrition report:",
            f"Analyzed meals: {int(meals_count or 0)}",
            f"Total estimated calories: {round(float(total_calories or 0.0), 1)} kcal",
            f"Average calories per analyzed meal: {round(float(average_calories or 0.0), 1)} kcal",
        ]
        if targets is not None:
            lines.append(f"Estimated daily target: {targets.calories} kcal")
        lines.append("Use this report as an approximation, not as medical certainty.")
        return "\n".join(lines)
