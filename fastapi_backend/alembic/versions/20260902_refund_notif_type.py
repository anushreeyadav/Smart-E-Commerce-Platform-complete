"""add refund_processed notification type

Revision ID: 20260902_refund_notif_type
Revises: 20260902_return_status_lifecycle
Create Date: 2026-09-02
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_refund_notif_type"
down_revision: Union[str, Sequence[str], None] = "20260902_return_status_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
                ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'REFUND_PROCESSED';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Intentionally non-destructive: Postgres cannot drop individual enum
    # values without recreating the type, and existing notifications may use them.
    pass
