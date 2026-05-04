from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, inspect, text

from app.config import get_settings


REQUIRED_TABLES = (
    "users",
    "user_profiles",
    "user_preferences",
    "user_consents",
    "access_requests",
    "model_registry",
)


@dataclass(slots=True)
class SchemaStatus:
    database_name: str
    current_schema: str
    search_path: str
    detected_tables: list[str]
    missing_tables: list[str]

    @property
    def ready(self) -> bool:
        return not self.missing_tables


def get_schema_status() -> SchemaStatus:
    settings = get_settings()
    engine = create_engine(settings.sync_database_url, connect_args=settings.sync_connect_args)
    try:
        with engine.connect() as conn:
            database_name = conn.execute(text("select current_database()")).scalar_one()
            current_schema = conn.execute(text("select current_schema()")).scalar_one()
            search_path = conn.execute(text("show search_path")).scalar_one()
            inspector = inspect(conn)
            detected_tables = sorted(inspector.get_table_names(schema="public"))
            missing_tables = [table for table in REQUIRED_TABLES if table not in detected_tables]
            return SchemaStatus(
                database_name=database_name,
                current_schema=current_schema,
                search_path=search_path,
                detected_tables=detected_tables,
                missing_tables=missing_tables,
            )
    finally:
        engine.dispose()
