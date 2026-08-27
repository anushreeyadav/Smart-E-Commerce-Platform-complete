"""add non-destructive user account status

Revision ID: 20260826_user_account_status
Revises: 20260824_notifications
Create Date: 2026-08-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260826_user_account_status"
down_revision: Union[str, Sequence[str], None] = "20260824_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing users remain active; no user records or keys are changed.
    op.execute(
        "ALTER TABLE users "
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;"
    )


def downgrade() -> None:
    # Deliberately left non-destructive: production user account state must not
    # be discarded by a rollback.
    pass
