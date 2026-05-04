from __future__ import annotations

from app.db.enums import AIRoute
from app.integrations.ai.orchestrator import AIOrchestrator
from app.repositories.meals import MealRepository
from app.schemas.ai import MealPlanDraft
from app.services.nutrition import build_profile_summary, calculate_daily_targets
from app.utils import extract_json_payload, load_prompt


class MealPlanService:
    def __init__(self, orchestrator: AIOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.meals = MealRepository()

    async def generate_starter_plan(self, session, user) -> object:
        profile = user.profile
        if profile is None:
            raise RuntimeError("Cannot generate meal plan without user profile")

        prompt = load_prompt("meal_plan")
        summary = build_profile_summary(profile, user.preferences)
        try:
            response = await self.orchestrator.request(
                route=AIRoute.CHAT,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": summary},
                ],
                session=session,
                user_id=user.id,
                prompt_name="meal_plan",
            )
            draft = MealPlanDraft.model_validate(extract_json_payload(response.text))
            provider = response.provider
            model_name = response.model
        except Exception:
            draft = self._fallback_plan(profile)
            provider = None
            model_name = None

        return await self.meals.create_meal_plan(
            session=session,
            user_id=user.id,
            summary=draft.summary,
            provider=provider,
            model_name=model_name,
            items=[item.model_dump() for item in draft.items],
        )

    def _fallback_plan(self, profile) -> MealPlanDraft:
        targets = calculate_daily_targets(profile)
        return MealPlanDraft(
            summary=(
                f"Daily target: about {targets.calories} kcal with focus on portion control, regular protein intake, and stable eating routine."
            ),
            items=[
                {
                    "meal_type": "breakfast",
                    "title": "Protein breakfast",
                    "description": "Eggs or cottage cheese with vegetables and whole grains.",
                    "calories_target": round(targets.calories * 0.25),
                    "protein_target": round(targets.protein_g * 0.25),
                },
                {
                    "meal_type": "lunch",
                    "title": "Balanced lunch",
                    "description": "Lean protein, complex carbs, and a large vegetable portion.",
                    "calories_target": round(targets.calories * 0.35),
                    "protein_target": round(targets.protein_g * 0.35),
                },
                {
                    "meal_type": "dinner",
                    "title": "Light dinner",
                    "description": "Protein with vegetables and moderate healthy fats.",
                    "calories_target": round(targets.calories * 0.25),
                    "protein_target": round(targets.protein_g * 0.25),
                },
                {
                    "meal_type": "snack",
                    "title": "Controlled snack",
                    "description": "Fruit with yogurt or nuts in measured portions.",
                    "calories_target": round(targets.calories * 0.15),
                    "protein_target": round(targets.protein_g * 0.15),
                },
            ],
        )
