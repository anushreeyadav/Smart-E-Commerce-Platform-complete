"""add non-destructive product activation

Revision ID: 20260826_product_activation
Revises: 20260826_user_account_status
Create Date: 2026-08-26
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260826_product_activation"
down_revision: Union[str, Sequence[str], None] = "20260826_user_account_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing products remain visible and purchasable after the upgrade.
    op.execute(
        "ALTER TABLE products "
        "ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_products_is_active "
        "ON products (is_active);"
    )


def downgrade() -> None:
    # Intentionally non-destructive: do not discard product activation state.
    pass
