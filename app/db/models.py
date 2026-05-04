from __future__ import annotations

from datetime import datetime, time
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.db.enums import (
    AIRoute,
    AIRequestStatus,
    AccessRequestStatus,
    ChatCategory,
    ChatDirection,
    DeletionScope,
    DeletionStatus,
    MealEntryStatus,
    ReminderType,
    UserRole,
    UserStatus,
)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    telegram_language_code: Mapped[str | None] = mapped_column(String(16))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus), default=UserStatus.PENDING, nullable=False, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_reason: Mapped[str | None] = mapped_column(Text)

    access_requests: Mapped[list[AccessRequest]] = relationship(
        back_populates="user", foreign_keys="AccessRequest.user_id"
    )
    profile: Mapped[UserProfile | None] = relationship(back_populates="user", uselist=False)
    preferences: Mapped[UserPreference | None] = relationship(back_populates="user", uselist=False)
    consents: Mapped[UserConsent | None] = relationship(back_populates="user", uselist=False)
    meal_entries: Mapped[list[MealEntry]] = relationship(back_populates="user")
    chat_messages: Mapped[list[ChatMessage]] = relationship(back_populates="user")
    reminders: Mapped[list[Reminder]] = relationship(back_populates="user")
    meal_plans: Mapped[list[MealPlan]] = relationship(back_populates="user")


class AccessRequest(Base, TimestampMixin):
    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[AccessRequestStatus] = mapped_column(
        Enum(AccessRequestStatus), default=AccessRequestStatus.PENDING, nullable=False, index=True
    )
    request_note: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="access_requests")


class UserProfile(Base, TimestampMixin):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str] = mapped_column(String(255))
    age: Mapped[int] = mapped_column(Integer)
    sex: Mapped[str] = mapped_column(String(32))
    height_cm: Mapped[float] = mapped_column(Float)
    weight_kg: Mapped[float] = mapped_column(Float)
    goal: Mapped[str] = mapped_column(String(255))
    activity_level: Mapped[str] = mapped_column(String(64))
    diseases_or_conditions: Mapped[str | None] = mapped_column(Text)
    country_region: Mapped[str] = mapped_column(String(255))

    user: Mapped[User] = relationship(back_populates="profile")


class UserPreference(Base, TimestampMixin):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    allergies: Mapped[str | None] = mapped_column(Text)
    favorite_foods: Mapped[str | None] = mapped_column(Text)
    disliked_foods: Mapped[str | None] = mapped_column(Text)
    budget: Mapped[str | None] = mapped_column(String(255))
    preferred_language: Mapped[str] = mapped_column(String(16), default="ru", nullable=False)

    user: Mapped[User] = relationship(back_populates="preferences")


class UserConsent(Base, TimestampMixin):
    __tablename__ = "user_consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="consents")


class MealEntry(Base, TimestampMixin):
    __tablename__ = "meal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[MealEntryStatus] = mapped_column(
        Enum(MealEntryStatus), default=MealEntryStatus.CLARIFYING, nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), default="photo")
    already_eaten: Mapped[bool | None] = mapped_column(Boolean)
    initial_vision_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    photo_deleted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[User] = relationship(back_populates="meal_entries")
    clarifications: Mapped[list[MealClarification]] = relationship(back_populates="meal_entry")
    analysis_result: Mapped[MealAnalysisResult | None] = relationship(
        back_populates="meal_entry", uselist=False
    )


class MealClarification(Base, TimestampMixin):
    __tablename__ = "meal_clarifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_entry_id: Mapped[int] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="CASCADE"), index=True
    )
    question_key: Mapped[str] = mapped_column(String(64))
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    meal_entry: Mapped[MealEntry] = relationship(back_populates="clarifications")


class MealAnalysisResult(Base, TimestampMixin):
    __tablename__ = "meal_analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_entry_id: Mapped[int] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="CASCADE"), unique=True
    )
    provider: Mapped[str | None] = mapped_column(String(64))
    model_name: Mapped[str | None] = mapped_column(String(255))
    recognized_foods: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    estimated_calories: Mapped[float | None] = mapped_column(Float)
    protein_g: Mapped[float | None] = mapped_column(Float)
    fat_g: Mapped[float | None] = mapped_column(Float)
    carbs_g: Mapped[float | None] = mapped_column(Float)
    confidence_note: Mapped[str | None] = mapped_column(Text)
    goal_fit_assessment: Mapped[str | None] = mapped_column(Text)
    improvement_advice: Mapped[str | None] = mapped_column(Text)
    alternative_suggestion: Mapped[str | None] = mapped_column(Text)
    corrected_summary: Mapped[str | None] = mapped_column(Text)
    structured_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    meal_entry: Mapped[MealEntry] = relationship(back_populates="analysis_result")


class ChatMessage(Base, TimestampMixin):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    related_meal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="SET NULL")
    )
    direction: Mapped[ChatDirection] = mapped_column(Enum(ChatDirection), nullable=False)
    category: Mapped[ChatCategory] = mapped_column(Enum(ChatCategory), nullable=False)
    locale: Mapped[str | None] = mapped_column(String(16))
    message_text: Mapped[str] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="chat_messages")


class Reminder(Base, TimestampMixin):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("user_id", "reminder_type", name="uq_reminder_user_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reminder_type: Mapped[ReminderType] = mapped_column(Enum(ReminderType), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reminder_time: Mapped[time] = mapped_column(nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    user: Mapped[User] = relationship(back_populates="reminders")


class NotificationLog(Base, TimestampMixin):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reminder_id: Mapped[int | None] = mapped_column(ForeignKey("reminders.id", ondelete="SET NULL"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message_text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MealPlan(Base, TimestampMixin):
    __tablename__ = "meal_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    summary: Mapped[str] = mapped_column(Text)
    generated_by_provider: Mapped[str | None] = mapped_column(String(64))
    generated_by_model: Mapped[str | None] = mapped_column(String(255))
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="meal_plans")
    items: Mapped[list[MealPlanItem]] = relationship(back_populates="meal_plan")


class MealPlanItem(Base, TimestampMixin):
    __tablename__ = "meal_plan_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    meal_plan_id: Mapped[int] = mapped_column(ForeignKey("meal_plans.id", ondelete="CASCADE"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meal_type: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    calories_target: Mapped[float | None] = mapped_column(Float)
    protein_target: Mapped[float | None] = mapped_column(Float)
    fat_target: Mapped[float | None] = mapped_column(Float)
    carbs_target: Mapped[float | None] = mapped_column(Float)

    meal_plan: Mapped[MealPlan] = relationship(back_populates="items")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint("provider", "route", "model_name", name="uq_model_registry_entry"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    route: Mapped[AIRoute] = mapped_column(Enum(AIRoute), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AIRequestLog(Base, TimestampMixin):
    __tablename__ = "ai_request_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    meal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("meal_entries.id", ondelete="SET NULL"), index=True
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    route: Mapped[AIRoute] = mapped_column(Enum(AIRoute), nullable=False)
    status: Mapped[AIRequestStatus] = mapped_column(Enum(AIRequestStatus), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_name: Mapped[str | None] = mapped_column(String(128))
    request_excerpt: Mapped[str | None] = mapped_column(Text)
    response_excerpt: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)


class AIFallbackLog(Base, TimestampMixin):
    __tablename__ = "ai_fallback_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_log_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_request_logs.id", ondelete="SET NULL")
    )
    from_provider: Mapped[str | None] = mapped_column(String(64))
    from_model: Mapped[str | None] = mapped_column(String(255))
    to_provider: Mapped[str | None] = mapped_column(String(64))
    to_model: Mapped[str | None] = mapped_column(String(255))
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class DeletionRequest(Base, TimestampMixin):
    __tablename__ = "deletion_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope: Mapped[DeletionScope] = mapped_column(Enum(DeletionScope), nullable=False)
    status: Mapped[DeletionStatus] = mapped_column(
        Enum(DeletionStatus), default=DeletionStatus.PENDING, nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserBlock(Base, TimestampMixin):
    __tablename__ = "user_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    blocked_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    unblocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
