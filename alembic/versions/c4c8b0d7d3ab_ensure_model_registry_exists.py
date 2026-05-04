"""ensure model_registry exists

Revision ID: c4c8b0d7d3ab
Revises: 8c293d0b996f
Create Date: 2026-04-10 01:30:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "c4c8b0d7d3ab"
down_revision = "8c293d0b996f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'airoute'
            ) THEN
                CREATE TYPE airoute AS ENUM ('VISION', 'CHAT', 'EMERGENCY');
            END IF;
        END
        $$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            id SERIAL PRIMARY KEY,
            provider VARCHAR(64) NOT NULL,
            route airoute NOT NULL,
            model_name VARCHAR(255) NOT NULL,
            priority INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'uq_model_registry_entry'
            ) THEN
                ALTER TABLE model_registry
                ADD CONSTRAINT uq_model_registry_entry
                UNIQUE (provider, route, model_name);
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    pass
