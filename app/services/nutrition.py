from __future__ import annotations

from dataclasses import dataclass

from app.db.models import UserPreference, UserProfile


@dataclass(slots=True)
class DailyTargets:
    calories: int
    protein_g: int
    fat_g: int
    carbs_g: int


def calculate_daily_targets(profile: UserProfile) -> DailyTargets:
    sex_factor = 5 if profile.sex.lower() in {"male", "man", "erkak", "мужской", "erkaklar"} else -161
    bmr = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age + sex_factor
    activity_map = {
        "low": 1.2,
        "sedentary": 1.2,
        "moderate": 1.375,
        "medium": 1.375,
        "active": 1.55,
        "high": 1.725,
    }
    multiplier = activity_map.get(profile.activity_level.lower(), 1.375)
    calories = int(bmr * multiplier)

    goal_text = profile.goal.lower()
    if "похуд" in goal_text or "weight loss" in goal_text or "ozish" in goal_text:
        calories -= 350
    elif "muscle" in goal_text or "набор" in goal_text:
        calories += 250

    calories = max(calories, 1200)
    protein = int(max(profile.weight_kg * 1.6, 80))
    fat = int(max(profile.weight_kg * 0.8, 45))
    carbs = int(max((calories - protein * 4 - fat * 9) / 4, 100))
    return DailyTargets(calories=calories, protein_g=protein, fat_g=fat, carbs_g=carbs)


def build_profile_summary(profile: UserProfile, preferences: UserPreference | None) -> str:
    preference_lines = []
    if preferences is not None:
        if preferences.allergies:
            preference_lines.append(f"Allergies: {preferences.allergies}")
        if preferences.favorite_foods:
            preference_lines.append(f"Favorite foods: {preferences.favorite_foods}")
        if preferences.disliked_foods:
            preference_lines.append(f"Disliked foods: {preferences.disliked_foods}")
        if preferences.budget:
            preference_lines.append(f"Budget: {preferences.budget}")

    targets = calculate_daily_targets(profile)
    joined_preferences = "\n".join(preference_lines) if preference_lines else "No additional preferences."
    return (
        f"Name: {profile.full_name}\n"
        f"Age: {profile.age}\n"
        f"Sex: {profile.sex}\n"
        f"Height: {profile.height_cm} cm\n"
        f"Weight: {profile.weight_kg} kg\n"
        f"Goal: {profile.goal}\n"
        f"Activity level: {profile.activity_level}\n"
        f"Diseases or conditions: {profile.diseases_or_conditions or 'None'}\n"
        f"Country or region: {profile.country_region}\n"
        f"Daily calorie target: {targets.calories} kcal\n"
        f"Daily protein target: {targets.protein_g} g\n"
        f"Daily fat target: {targets.fat_g} g\n"
        f"Daily carbs target: {targets.carbs_g} g\n"
        f"Preferences:\n{joined_preferences}"
    )
