"""backfill existing orders to the inr-only currency model

Revision ID: 20260831_backfill_inr_currency
Revises: 20260831_orderstatus_fix
Create Date: 2026-08-31

The store now only checks out in INR (see 20260831_orderstatus_fix and the
app-level currency changes) and product prices were always entered as rupee
amounts, never USD. Orders placed before this change are stamped
currency='usd' purely because that used to be the code default — the
total_amount figures were never actually multiplied by an FX rate, so no
monetary conversion is needed here, only relabeling.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_backfill_inr_currency"
down_revision: Union[str, Sequence[str], None] = "20260831_orderstatus_fix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE orders SET currency = 'inr' WHERE currency <> 'inr';")


def downgrade() -> None:
    # Intentionally non-destructive: the original per-order currency label
    # is not recoverable once overwritten, and downgrading shouldn't
    # re-mislabel historical orders as 'usd'.
    pass
