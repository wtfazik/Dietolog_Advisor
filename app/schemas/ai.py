from __future__ import annotations

from pydantic import BaseModel, Field


class RecognizedFood(BaseModel):
    name: str
    estimated_grams: float | None = None
    estimated_pieces: float | None = None
    calories: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None


class VisionDraft(BaseModel):
    recognized_items: list[str] = Field(default_factory=list)
    uncertainty_note: str
    follow_up_focus: list[str] = Field(default_factory=list)


class FinalMealAnalysis(BaseModel):
    recognized_foods: list[RecognizedFood] = Field(default_factory=list)
    estimated_calories: float
    protein_g: float
    fat_g: float
    carbs_g: float
    confidence_note: str
    goal_fit_assessment: str
    improvement_advice: str
    alternative_suggestion: str | None = None
    approximation_note: str


class MealPlanItemDraft(BaseModel):
    meal_type: str
    title: str
    description: str
    calories_target: float | None = None
    protein_target: float | None = None
    fat_target: float | None = None
    carbs_target: float | None = None


class MealPlanDraft(BaseModel):
    summary: str
    items: list[MealPlanItemDraft] = Field(default_factory=list)


class TopicClassification(BaseModel):
    is_nutrition_related: bool
    reason: str
