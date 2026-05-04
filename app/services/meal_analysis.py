from __future__ import annotations

import base64

from app.db.enums import AIRoute, ChatCategory, ChatDirection
from app.integrations.ai.orchestrator import AIOrchestrator
from app.repositories.meals import MealRepository
from app.schemas.ai import FinalMealAnalysis, VisionDraft
from app.services.nutrition import build_profile_summary
from app.utils import extract_json_payload, load_prompt


CLARIFICATION_QUESTIONS = [
    ("composition", "meal_question_composition"),
    ("grams", "meal_question_grams"),
    ("pieces", "meal_question_pieces"),
    ("origin", "meal_question_origin"),
    ("timing", "meal_question_timing"),
    ("extras", "meal_question_extras"),
]


class MealAnalysisService:
    def __init__(self, orchestrator: AIOrchestrator) -> None:
        self.orchestrator = orchestrator
        self.meals = MealRepository()

    async def start_photo_analysis(self, session, user, photo_bytes: bytes) -> tuple[object, VisionDraft]:
        encoded_photo = base64.b64encode(photo_bytes).decode("ascii")
        prompt = load_prompt("meal_vision")
        response = await self.orchestrator.request(
            route=AIRoute.VISION,
            messages=[
                {"role": "system", "content": prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Analyze this meal photo for nutrition guidance."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_photo}"}},
                    ],
                },
            ],
            session=session,
            user_id=user.id,
            prompt_name="meal_vision",
        )
        draft = VisionDraft.model_validate(extract_json_payload(response.text))
        meal_entry = await self.meals.create_meal_entry(
            session=session,
            user_id=user.id,
            initial_vision_summary=draft.model_dump(),
        )
        await self.meals.log_chat_message(
            session=session,
            user_id=user.id,
            direction=ChatDirection.INBOUND,
            category=ChatCategory.MEAL_ANALYSIS,
            text="[photo uploaded for meal analysis]",
            locale=(user.preferences.preferred_language if user.preferences else None),
            related_meal_entry_id=meal_entry.id,
        )
        return meal_entry, draft

    async def save_clarification(
        self,
        session,
        meal_entry_id: int,
        question_key: str,
        question_text: str,
        answer_text: str,
        sort_order: int,
        user_id: int,
        locale: str | None,
    ) -> None:
        await self.meals.add_clarification(
            session=session,
            meal_entry_id=meal_entry_id,
            question_key=question_key,
            question_text=question_text,
            answer_text=answer_text,
            sort_order=sort_order,
        )
        await self.meals.log_chat_message(
            session=session,
            user_id=user_id,
            direction=ChatDirection.INBOUND,
            category=ChatCategory.MEAL_ANALYSIS,
            text=answer_text,
            locale=locale,
            related_meal_entry_id=meal_entry_id,
        )

    async def finalize_analysis(self, session, user, meal_entry_id: int) -> FinalMealAnalysis:
        meal_entry = await self.meals.get_meal_entry(session, meal_entry_id)
        if meal_entry is None:
            raise RuntimeError("Meal entry not found")

        clarifications = {
            item.question_key: item.answer_text
            for item in sorted(meal_entry.clarifications, key=lambda row: row.sort_order)
        }
        profile_summary = build_profile_summary(user.profile, user.preferences) if user.profile else "No profile"
        prompt = load_prompt("meal_finalize")
        try:
            response = await self.orchestrator.request(
                route=AIRoute.CHAT,
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            f"User profile:\n{profile_summary}\n\n"
                            f"Initial meal vision result:\n{meal_entry.initial_vision_summary}\n\n"
                            f"Clarifications:\n{clarifications}"
                        ),
                    },
                ],
                session=session,
                user_id=user.id,
                meal_entry_id=meal_entry.id,
                prompt_name="meal_finalize",
            )
            payload = extract_json_payload(response.text)
            analysis = FinalMealAnalysis.model_validate(payload)
            await self.meals.complete_meal_analysis(
                session=session,
                meal_entry=meal_entry,
                payload=analysis.model_dump(),
                provider=response.provider,
                model_name=response.model,
            )
            return analysis
        except Exception:
            await self.meals.mark_meal_failed(session, meal_entry)
            raise
