"""add checkout stripe columns

Revision ID: 20260819_checkout_stripe
Revises: None
Create Date: 2026-08-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260819_checkout_stripe"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE orders
            ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'usd',
            ADD COLUMN IF NOT EXISTS stripe_checkout_session_id VARCHAR(120),
            ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(120);
        """
    )
    op.execute(
        """
        ALTER TABLE payments
            ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) NOT NULL DEFAULT 'stripe';
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'orderstatus'
            ) THEN
                BEGIN
                    ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'confirmed';
                EXCEPTION
                    WHEN duplicate_object THEN
                        NULL;
                END;

                BEGIN
                    ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'paid';
                EXCEPTION
                    WHEN duplicate_object THEN
                        NULL;
                END;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_stripe_checkout_session_id
            ON orders (stripe_checkout_session_id)
            WHERE stripe_checkout_session_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_stripe_payment_intent_id
            ON orders (stripe_payment_intent_id)
            WHERE stripe_payment_intent_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_orders_stripe_payment_intent_id;")
    op.execute("DROP INDEX IF EXISTS ix_orders_stripe_checkout_session_id;")
    op.drop_column("payments", "payment_method")
    op.drop_column("orders", "stripe_payment_intent_id")
    op.drop_column("orders", "stripe_checkout_session_id")
    op.drop_column("orders", "currency")
    op.drop_column("orders", "payment_status")
