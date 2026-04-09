from __future__ import annotations

from app.db.enums import AIRoute
from app.integrations.ai.orchestrator import AIOrchestrator
from app.schemas.ai import TopicClassification
from app.utils import extract_json_payload, load_prompt


class TopicGuardService:
    KEYWORDS = {
        "calories",
        "calorie",
        "protein",
        "fat",
        "carbs",
        "diet",
        "nutrition",
        "meal",
        "weight",
        "food",
        "kcal",
        "калории",
        "белки",
        "жиры",
        "углеводы",
        "питание",
        "диета",
        "вес",
        "еда",
        "рацион",
        "калория",
        "ovqat",
        "parhez",
        "ratsion",
        "vazn",
        "kaloriya",
        "oqsil",
        "uglevod",
        "yog",
    }

    def __init__(self, orchestrator: AIOrchestrator) -> None:
        self.orchestrator = orchestrator

    async def classify(
        self, text: str, session=None, user_id: int | None = None
    ) -> TopicClassification:
        lowered = text.lower()
        if any(keyword in lowered for keyword in self.KEYWORDS):
            return TopicClassification(is_nutrition_related=True, reason="keyword_match")

        prompt = load_prompt("nutrition_guard")
        try:
            response = await self.orchestrator.request(
                route=AIRoute.EMERGENCY,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text},
                ],
                session=session,
                user_id=user_id,
                prompt_name="nutrition_guard",
            )
            return TopicClassification.model_validate(extract_json_payload(response.text))
        except Exception:
            return TopicClassification(
                is_nutrition_related=False,
                reason="classifier_unavailable",
            )
