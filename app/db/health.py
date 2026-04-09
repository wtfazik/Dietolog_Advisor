from __future__ import annotations

from sqlalchemy import text


REQUIRED_TABLES = (
    "users",
    "user_profiles",
    "user_preferences",
    "user_consents",
    "access_requests",
    "model_registry",
)


async def get_missing_required_tables(session) -> list[str]:
    missing: list[str] = []
    for table_name in REQUIRED_TABLES:
        result = await session.execute(
            text("select to_regclass(:table_name)"), {"table_name": table_name}
        )
        if result.scalar_one_or_none() is None:
            missing.append(table_name)
    return missing


async def schema_ready(session) -> bool:
    return not await get_missing_required_tables(session)
