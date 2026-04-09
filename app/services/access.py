from __future__ import annotations

from app.db.enums import UserRole, UserStatus
from app.repositories.admin import AdminRepository
from app.repositories.users import UserRepository


class AccessService:
    def __init__(self, settings) -> None:
        self.settings = settings
        self.users = UserRepository()
        self.admin = AdminRepository()

    async def get_or_create_user_from_telegram(self, session, telegram_user) -> object:
        return await self.users.get_or_create(
            session=session,
            telegram_user_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name,
            telegram_language_code=telegram_user.language_code,
            superadmin_telegram_id=self.settings.superadmin_telegram_id,
        )

    async def submit_access_request(self, session, user, note: str | None = None):
        existing = await self.users.get_pending_access_request_for_user(session, user.id)
        if existing is not None:
            return existing, False
        request = await self.users.create_access_request(session, user, note)
        await self.admin.create_audit_log(
            session,
            action="access_request_submitted",
            actor_user_id=user.id,
            target_user_id=user.id,
            details={"request_id": request.id},
        )
        return request, True

    async def approve_request(self, session, request_id: int, reviewer_id: int | None):
        access_request = await self.users.get_access_request(session, request_id)
        if access_request is None:
            return None
        await self.users.approve_access_request(session, access_request, reviewer_id)
        await self.admin.create_audit_log(
            session,
            action="access_request_approved",
            actor_user_id=reviewer_id,
            target_user_id=access_request.user_id,
            details={"request_id": access_request.id},
        )
        return access_request

    async def reject_request(self, session, request_id: int, reviewer_id: int | None, reason: str | None):
        access_request = await self.users.get_access_request(session, request_id)
        if access_request is None:
            return None
        await self.users.reject_access_request(session, access_request, reviewer_id, reason)
        await self.admin.create_audit_log(
            session,
            action="access_request_rejected",
            actor_user_id=reviewer_id,
            target_user_id=access_request.user_id,
            details={"request_id": access_request.id, "reason": reason},
        )
        return access_request

    def is_superadmin(self, user) -> bool:
        return user.role == UserRole.SUPERADMIN

    def is_allowed(self, user) -> bool:
        return user.status == UserStatus.APPROVED
