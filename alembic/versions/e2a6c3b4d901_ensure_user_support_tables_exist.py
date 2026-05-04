"""ensure user support tables exist

Revision ID: e2a6c3b4d901
Revises: f0d9d8f7c1a2
Create Date: 2026-04-10 02:45:00.000000

"""

from __future__ import annotations

from alembic import op


revision = "e2a6c3b4d901"
down_revision = "f0d9d8f7c1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            allergies TEXT,
            favorite_foods TEXT,
            disliked_foods TEXT,
            budget VARCHAR(255),
            preferred_language VARCHAR(16) NOT NULL DEFAULT 'ru',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_consents (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            disclaimer_accepted_at TIMESTAMPTZ,
            privacy_accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )


def downgrade() -> None:
    pass
