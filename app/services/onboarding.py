from __future__ import annotations

from dataclasses import dataclass

from app.repositories.users import UserRepository


@dataclass(frozen=True, slots=True)
class OnboardingStep:
    key: str
    prompt_key: str
    optional: bool = False
    numeric: bool = False


ONBOARDING_STEPS = [
    OnboardingStep("full_name", "onboarding_name"),
    OnboardingStep("age", "onboarding_age", numeric=True),
    OnboardingStep("sex", "onboarding_sex"),
    OnboardingStep("height_cm", "onboarding_height", numeric=True),
    OnboardingStep("weight_kg", "onboarding_weight", numeric=True),
    OnboardingStep("goal", "onboarding_goal"),
    OnboardingStep("activity_level", "onboarding_activity"),
    OnboardingStep("allergies", "onboarding_allergies", optional=True),
    OnboardingStep("diseases_or_conditions", "onboarding_conditions", optional=True),
    OnboardingStep("favorite_foods", "onboarding_favorite_foods", optional=True),
    OnboardingStep("disliked_foods", "onboarding_disliked_foods", optional=True),
    OnboardingStep("budget", "onboarding_budget", optional=True),
    OnboardingStep("country_region", "onboarding_country"),
    OnboardingStep("preferred_language", "onboarding_language"),
]


class OnboardingService:
    def __init__(self) -> None:
        self.users = UserRepository()

    def steps(self) -> list[OnboardingStep]:
        return ONBOARDING_STEPS

    def validate_answer(self, step: OnboardingStep, answer: str) -> object:
        cleaned = answer.strip()
        if step.optional and cleaned in {"-", "нет", "yo'q", "йўқ", "skip"}:
            return None
        if step.numeric:
            value = float(cleaned.replace(",", "."))
            return int(value) if step.key == "age" else value
        if step.key == "preferred_language":
            if cleaned not in {"ru", "uz_cyrl", "uz_latn"}:
                raise ValueError("Language must be ru, uz_cyrl, or uz_latn")
        return cleaned

    async def persist_answers(self, session, user_id: int, answers: dict[str, object]) -> None:
        profile_data = {
            "full_name": answers["full_name"],
            "age": answers["age"],
            "sex": answers["sex"],
            "height_cm": answers["height_cm"],
            "weight_kg": answers["weight_kg"],
            "goal": answers["goal"],
            "activity_level": answers["activity_level"],
            "diseases_or_conditions": answers.get("diseases_or_conditions"),
            "country_region": answers["country_region"],
        }
        preference_data = {
            "allergies": answers.get("allergies"),
            "favorite_foods": answers.get("favorite_foods"),
            "disliked_foods": answers.get("disliked_foods"),
            "budget": answers.get("budget"),
            "preferred_language": answers.get("preferred_language", "ru"),
        }
        await self.users.upsert_profile(session, user_id, profile_data, preference_data)
