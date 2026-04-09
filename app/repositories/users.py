from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.enums import AccessRequestStatus, UserRole, UserStatus
from app.db.models import AccessRequest, User, UserConsent, UserPreference, UserProfile


class UserRepository:
    async def get_by_telegram_id(self, session, telegram_user_id: int) -> User | None:
        result = await session.execute(select(User).where(User.telegram_user_id == telegram_user_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, session, user_id: int) -> User | None:
        result = await session.execute(
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.preferences),
                selectinload(User.consents),
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        telegram_language_code: str | None,
        superadmin_telegram_id: int | None,
    ) -> User:
        user = await self.get_by_telegram_id(session, telegram_user_id)
        if user is not None:
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.telegram_language_code = telegram_language_code
            return user

        role = UserRole.SUPERADMIN if telegram_user_id == superadmin_telegram_id else UserRole.USER
        status = UserStatus.APPROVED if role == UserRole.SUPERADMIN else UserStatus.PENDING
        approved_at = datetime.now(timezone.utc) if status == UserStatus.APPROVED else None
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            telegram_language_code=telegram_language_code,
            role=role,
            status=status,
            approved_at=approved_at,
        )
        session.add(user)
        await session.flush()
        return user

    async def create_access_request(self, session, user: User, note: str | None = None) -> AccessRequest:
        access_request = AccessRequest(user_id=user.id, request_note=note)
        session.add(access_request)
        await session.flush()
        return access_request

    async def get_pending_access_request_for_user(self, session, user_id: int) -> AccessRequest | None:
        result = await session.execute(
            select(AccessRequest)
            .where(
                AccessRequest.user_id == user_id,
                AccessRequest.status == AccessRequestStatus.PENDING,
            )
            .order_by(AccessRequest.created_at.desc())
        )
        return result.scalars().first()

    async def get_access_request(self, session, request_id: int) -> AccessRequest | None:
        result = await session.execute(
            select(AccessRequest)
            .options(selectinload(AccessRequest.user))
            .where(AccessRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def list_pending_access_requests(self, session, limit: int = 50) -> list[AccessRequest]:
        result = await session.execute(
            select(AccessRequest)
            .options(selectinload(AccessRequest.user))
            .where(AccessRequest.status == AccessRequestStatus.PENDING)
            .order_by(AccessRequest.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars())

    async def approve_access_request(self, session, access_request: AccessRequest, reviewer_id: int | None) -> None:
        access_request.status = AccessRequestStatus.APPROVED
        access_request.reviewed_by_user_id = reviewer_id
        access_request.reviewed_at = datetime.now(timezone.utc)
        access_request.user.status = UserStatus.APPROVED
        access_request.user.approved_at = datetime.now(timezone.utc)

    async def reject_access_request(
        self,
        session,
        access_request: AccessRequest,
        reviewer_id: int | None,
        reason: str | None,
    ) -> None:
        access_request.status = AccessRequestStatus.REJECTED
        access_request.reviewed_by_user_id = reviewer_id
        access_request.reviewed_at = datetime.now(timezone.utc)
        access_request.review_note = reason
        access_request.user.status = UserStatus.REJECTED

    async def upsert_profile(
        self,
        session,
        user_id: int,
        profile_data: dict[str, object],
        preference_data: dict[str, object],
    ) -> tuple[UserProfile, UserPreference]:
        profile_result = await session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = profile_result.scalar_one_or_none()
        if profile is None:
            profile = UserProfile(user_id=user_id, **profile_data)
            session.add(profile)
        else:
            for key, value in profile_data.items():
                setattr(profile, key, value)

        preference_result = await session.execute(
            select(UserPreference).where(UserPreference.user_id == user_id)
        )
        preferences = preference_result.scalar_one_or_none()
        if preferences is None:
            preferences = UserPreference(user_id=user_id, **preference_data)
            session.add(preferences)
        else:
            for key, value in preference_data.items():
                setattr(preferences, key, value)

        await session.flush()
        return profile, preferences

    async def upsert_consents(
        self,
        session,
        user_id: int,
        disclaimer_accepted: bool,
        privacy_accepted: bool,
    ) -> UserConsent:
        result = await session.execute(select(UserConsent).where(UserConsent.user_id == user_id))
        consent = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if consent is None:
            consent = UserConsent(user_id=user_id)
            session.add(consent)

        if disclaimer_accepted:
            consent.disclaimer_accepted_at = now
        if privacy_accepted:
            consent.privacy_accepted_at = now

        await session.flush()
        return consent

    async def list_users(self, session, limit: int = 100) -> list[User]:
        result = await session.execute(
            select(User)
            .options(selectinload(User.profile), selectinload(User.preferences))
            .order_by(User.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())
