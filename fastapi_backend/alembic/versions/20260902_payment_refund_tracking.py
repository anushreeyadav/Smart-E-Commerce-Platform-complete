"""track the stripe refund id and timestamp on payments

Revision ID: 20260902_payment_refund_tracking
Revises: 20260902_refund_notif_type
Create Date: 2026-09-02

Lets a refund's Stripe refund id (and when it completed) be persisted on the
payment record, so a processed refund is traceable back to the exact Stripe
object that moved the money, not just inferred from payment.status.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_payment_refund_tracking"
down_revision: Union[str, Sequence[str], None] = "20260902_refund_notif_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE payments
            ADD COLUMN IF NOT EXISTS stripe_refund_id VARCHAR(120),
            ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_stripe_refund_id
            ON payments (stripe_refund_id)
            WHERE stripe_refund_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_payments_stripe_refund_id;")
    op.drop_column("payments", "refunded_at")
    op.drop_column("payments", "stripe_refund_id")
