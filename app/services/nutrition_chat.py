from __future__ import annotations

from app.db.enums import AIRoute, ChatCategory, ChatDirection
from app.integrations.ai.orchestrator import AIOrchestrator
from app.repositories.meals import MealRepository
from app.services.nutrition import build_profile_summary
from app.services.topic_guard import TopicGuardService
from app.utils import load_prompt


class NutritionChatService:
    def __init__(self, orchestrator: AIOrchestrator, topic_guard: TopicGuardService) -> None:
        self.orchestrator = orchestrator
        self.topic_guard = topic_guard
        self.meals = MealRepository()

    async def answer_question(self, session, user, text: str, locale: str) -> str:
        classification = await self.topic_guard.classify(text, session=session, user_id=user.id)
        if not classification.is_nutrition_related:
            refusal = "I only provide professional guidance on nutrition, healthy eating, meal composition, weight management, and related wellness topics."
            await self.meals.log_chat_message(
                session=session,
                user_id=user.id,
                direction=ChatDirection.INBOUND,
                category=ChatCategory.GENERAL,
                text=text,
                locale=locale,
            )
            await self.meals.log_chat_message(
                session=session,
                user_id=user.id,
                direction=ChatDirection.OUTBOUND,
                category=ChatCategory.SYSTEM,
                text=refusal,
                locale=locale,
            )
            return refusal

        prompt = load_prompt("nutrition_chat")
        profile_summary = (
            build_profile_summary(user.profile, user.preferences) if user.profile else "No profile"
        )
        try:
            response = await self.orchestrator.request(
                route=AIRoute.CHAT,
                messages=[
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": f"User profile:\n{profile_summary}\n\nQuestion:\n{text}",
                    },
                ],
                session=session,
                user_id=user.id,
                prompt_name="nutrition_chat",
            )
            answer_text = response.text
        except Exception:
            answer_text = "The nutrition assistant is temporarily unavailable. Please repeat the request later."
        await self.meals.log_chat_message(
            session=session,
            user_id=user.id,
            direction=ChatDirection.INBOUND,
            category=ChatCategory.NUTRITION_QA,
            text=text,
            locale=locale,
        )
        await self.meals.log_chat_message(
            session=session,
            user_id=user.id,
            direction=ChatDirection.OUTBOUND,
            category=ChatCategory.NUTRITION_QA,
            text=answer_text,
            locale=locale,
        )
        return answer_text
