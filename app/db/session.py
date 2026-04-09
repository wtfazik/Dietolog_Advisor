from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import get_settings


settings = get_settings()
engine_kwargs: dict[str, object] = {
    "pool_pre_ping": True,
    "connect_args": settings.async_connect_args,
}
if settings.uses_external_pooler:
    engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.async_database_url, **engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
