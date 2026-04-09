from __future__ import annotations

from sqlalchemy import text


REQUIRED_TABLES = (
    "users",
    "user_profiles",
    "access_requests",
    "meal_entries",
    "chat_messages",
    "model_registry",
)


async def schema_ready(session) -> bool:
    for table_name in REQUIRED_TABLES:
        result = await session.execute(
            text("select to_regclass(:table_name)"), {"table_name": table_name}
        )
        if result.scalar_one_or_none() is None:
            return False
    return True
