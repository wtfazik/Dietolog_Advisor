"""ensure core tables exist

Revision ID: f0d9d8f7c1a2
Revises: c4c8b0d7d3ab
Create Date: 2026-04-10 02:35:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "f0d9d8f7c1a2"
down_revision = "c4c8b0d7d3ab"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                CREATE TYPE userrole AS ENUM ('USER', 'SUPERADMIN');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstatus') THEN
                CREATE TYPE userstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'BLOCKED');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'accessrequeststatus') THEN
                CREATE TYPE accessrequeststatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'mealentrystatus') THEN
                CREATE TYPE mealentrystatus AS ENUM ('CLARIFYING', 'ANALYZED', 'FAILED');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chatdirection') THEN
                CREATE TYPE chatdirection AS ENUM ('INBOUND', 'OUTBOUND');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'chatcategory') THEN
                CREATE TYPE chatcategory AS ENUM ('GENERAL', 'NUTRITION_QA', 'MEAL_ANALYSIS', 'SYSTEM');
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            telegram_language_code VARCHAR(16),
            role userrole NOT NULL DEFAULT 'USER',
            status userstatus NOT NULL DEFAULT 'PENDING',
            approved_at TIMESTAMPTZ,
            blocked_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_users_status ON users (status);
        CREATE INDEX IF NOT EXISTS ix_users_telegram_user_id ON users (telegram_user_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            full_name VARCHAR(255) NOT NULL,
            age INTEGER NOT NULL,
            sex VARCHAR(32) NOT NULL,
            height_cm DOUBLE PRECISION NOT NULL,
            weight_kg DOUBLE PRECISION NOT NULL,
            goal VARCHAR(255) NOT NULL,
            activity_level VARCHAR(64) NOT NULL,
            diseases_or_conditions TEXT,
            country_region VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS access_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status accessrequeststatus NOT NULL DEFAULT 'PENDING',
            request_note TEXT,
            reviewed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ,
            review_note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_access_requests_status ON access_requests (status);
        CREATE INDEX IF NOT EXISTS ix_access_requests_user_id ON access_requests (user_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_entries (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            status mealentrystatus NOT NULL DEFAULT 'CLARIFYING',
            source_type VARCHAR(32) NOT NULL DEFAULT 'photo',
            already_eaten BOOLEAN,
            initial_vision_summary JSON,
            photo_deleted BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_meal_entries_status ON meal_entries (status);
        CREATE INDEX IF NOT EXISTS ix_meal_entries_user_id ON meal_entries (user_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_messages (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            related_meal_entry_id INTEGER REFERENCES meal_entries(id) ON DELETE SET NULL,
            direction chatdirection NOT NULL,
            category chatcategory NOT NULL,
            locale VARCHAR(16),
            message_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_chat_messages_user_id ON chat_messages (user_id);
        """
    )


def downgrade() -> None:
    pass
