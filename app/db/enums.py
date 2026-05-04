from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class AccessRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class UserRole(StrEnum):
    USER = "user"
    SUPERADMIN = "superadmin"


class ReminderType(StrEnum):
    MEAL = "meal"
    DAILY_REPORT = "daily_report"


class DeletionScope(StrEnum):
    HISTORY = "history"
    PROFILE_AND_HISTORY = "profile_and_history"
    FULL_ACCOUNT = "full_account"


class DeletionStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"


class ChatDirection(StrEnum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"


class ChatCategory(StrEnum):
    GENERAL = "general"
    NUTRITION_QA = "nutrition_qa"
    MEAL_ANALYSIS = "meal_analysis"
    SYSTEM = "system"


class MealEntryStatus(StrEnum):
    CLARIFYING = "clarifying"
    ANALYZED = "analyzed"
    FAILED = "failed"


class AIRoute(StrEnum):
    VISION = "vision"
    CHAT = "chat"
    EMERGENCY = "emergency"


class AIRequestStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
