"""add notification types for return request decisions

Revision ID: 20260831_return_notif_types
Revises: 20260831_order_mgmt
Create Date: 2026-08-31
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_return_notif_types"
down_revision: Union[str, Sequence[str], None] = "20260831_order_mgmt"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for value in ("RETURN_APPROVED", "RETURN_REJECTED"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
                    ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS '{value}';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # Intentionally non-destructive: Postgres cannot drop individual enum
    # values without recreating the type, and existing notifications may use them.
    pass
