from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from app.db.enums import UserStatus
from app.db.models import AIRequestLog, AuditLog, ModelRegistry, NotificationLog, User, UserBlock


class AdminRepository:
    async def create_audit_log(
        self,
        session,
        action: str,
        actor_user_id: int | None,
        target_user_id: int | None,
        details: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            action=action,
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            details=details,
        )
        session.add(entry)
        await session.flush()
        return entry

    async def list_recent_ai_logs(self, session, limit: int = 100) -> list[AIRequestLog]:
        result = await session.execute(
            select(AIRequestLog).order_by(AIRequestLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def list_recent_notification_logs(self, session, limit: int = 100) -> list[NotificationLog]:
        result = await session.execute(
            select(NotificationLog).order_by(NotificationLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars())

    async def list_model_registry(self, session) -> list[ModelRegistry]:
        result = await session.execute(
            select(ModelRegistry).order_by(ModelRegistry.provider, ModelRegistry.route, ModelRegistry.priority)
        )
        return list(result.scalars())

    async def upsert_model_registry_entry(
        self,
        session,
        provider: str,
        route,
        model_name: str,
        priority: int,
        is_active: bool = True,
    ) -> ModelRegistry:
        result = await session.execute(
            select(ModelRegistry).where(
                ModelRegistry.provider == provider,
                ModelRegistry.route == route,
                ModelRegistry.model_name == model_name,
            )
        )
        entry = result.scalar_one_or_none()
        if entry is None:
            entry = ModelRegistry(
                provider=provider,
                route=route,
                model_name=model_name,
                priority=priority,
                is_active=is_active,
            )
            session.add(entry)
        else:
            entry.priority = priority
            entry.is_active = is_active

        await session.flush()
        return entry

    async def get_model_registry_entry(self, session, entry_id: int) -> ModelRegistry | None:
        result = await session.execute(select(ModelRegistry).where(ModelRegistry.id == entry_id))
        return result.scalar_one_or_none()

    async def toggle_model_registry_entry(self, session, entry: ModelRegistry, is_active: bool) -> None:
        entry.is_active = is_active
        await session.flush()

    async def list_blocks(self, session, active_only: bool = True) -> list[UserBlock]:
        stmt = select(UserBlock)
        if active_only:
            stmt = stmt.where(UserBlock.active.is_(True))
        result = await session.execute(stmt.order_by(UserBlock.created_at.desc()))
        return list(result.scalars())

    async def block_user(
        self,
        session,
        user: User,
        reason: str | None,
        actor_user_id: int | None,
    ) -> UserBlock:
        user.status = UserStatus.BLOCKED
        user.blocked_reason = reason
        block = UserBlock(
            user_id=user.id,
            blocked_by_user_id=actor_user_id,
            reason=reason,
            active=True,
            blocked_at=datetime.now(timezone.utc),
        )
        session.add(block)
        await session.flush()
        return block

    async def unblock_user(self, session, user: User) -> None:
        user.status = UserStatus.APPROVED
        user.blocked_reason = None
        result = await session.execute(
            select(UserBlock)
            .where(UserBlock.user_id == user.id, UserBlock.active.is_(True))
            .order_by(UserBlock.created_at.desc())
        )
        block = result.scalars().first()
        if block is not None:
            block.active = False
            block.unblocked_at = datetime.now(timezone.utc)
        await session.flush()
