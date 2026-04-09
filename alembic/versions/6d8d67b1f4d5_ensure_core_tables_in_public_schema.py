"""ensure core tables in public schema

Revision ID: 6d8d67b1f4d5
Revises: e2a6c3b4d901
Create Date: 2026-04-10 03:00:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "6d8d67b1f4d5"
down_revision = "e2a6c3b4d901"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS public")
    op.execute("SET search_path TO public")

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'airoute') THEN
                CREATE TYPE public.airoute AS ENUM ('VISION', 'CHAT', 'EMERGENCY');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userrole') THEN
                CREATE TYPE public.userrole AS ENUM ('USER', 'SUPERADMIN');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userstatus') THEN
                CREATE TYPE public.userstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'BLOCKED');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'accessrequeststatus') THEN
                CREATE TYPE public.accessrequeststatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.users (
            id SERIAL PRIMARY KEY,
            telegram_user_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(255),
            first_name VARCHAR(255),
            last_name VARCHAR(255),
            telegram_language_code VARCHAR(16),
            role public.userrole NOT NULL DEFAULT 'USER',
            status public.userstatus NOT NULL DEFAULT 'PENDING',
            approved_at TIMESTAMPTZ,
            blocked_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_users_status ON public.users (status);
        CREATE INDEX IF NOT EXISTS ix_users_telegram_user_id ON public.users (telegram_user_id);
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.user_profiles (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
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
        CREATE TABLE IF NOT EXISTS public.user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
            allergies TEXT,
            favorite_foods TEXT,
            disliked_foods TEXT,
            budget VARCHAR(255),
            preferred_language VARCHAR(16) NOT NULL DEFAULT 'ru',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS public.user_consents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
            disclaimer_accepted_at TIMESTAMPTZ,
            privacy_accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE TABLE IF NOT EXISTS public.access_requests (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            status public.accessrequeststatus NOT NULL DEFAULT 'PENDING',
            request_note TEXT,
            reviewed_by_user_id INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
            reviewed_at TIMESTAMPTZ,
            review_note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_access_requests_status ON public.access_requests (status);
        CREATE INDEX IF NOT EXISTS ix_access_requests_user_id ON public.access_requests (user_id);
        CREATE TABLE IF NOT EXISTS public.model_registry (
            id SERIAL PRIMARY KEY,
            provider VARCHAR(64) NOT NULL,
            route public.airoute NOT NULL,
            model_name VARCHAR(255) NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_model_registry_entry UNIQUE (provider, route, model_name)
        );
        """
    )


def downgrade() -> None:
    pass
