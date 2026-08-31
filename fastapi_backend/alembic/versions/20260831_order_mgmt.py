"""order management: out-for-delivery status, status history, return review fields

Revision ID: 20260831_order_mgmt
Revises: 20260831_backfill_inr_currency
Create Date: 2026-08-31

Adds the schema needed for the Admin/Staff order-management + return-review
feature:
- OrderStatus.OUT_FOR_DELIVERY (new enum value, inserted between SHIPPED and
  DELIVERED; existing SHIPPED -> DELIVERED direct transition is preserved).
- orders.shipping_address, orders.updated_at (additive, nullable/defaulted).
- order_status_history: audit trail of every order status change.
- return_requests.reviewed_by / reviewed_at / review_comment: who
  approved/rejected a return request, when, and why.
- return_request_history: audit trail of every return-request status change.
No existing data, columns, or tables are removed or altered destructively.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_order_mgmt"
down_revision: Union[str, Sequence[str], None] = "20260831_backfill_inr_currency"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
                ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'OUT_FOR_DELIVERY';
            END IF;
        END $$;
        """
    )

    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;"
    )
    op.execute(
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at "
        "TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;"
    )

    op.execute(
        "CREATE TABLE IF NOT EXISTS order_status_history ("
        "id VARCHAR(36) PRIMARY KEY, "
        "order_id VARCHAR(36) NOT NULL REFERENCES orders(id) ON DELETE CASCADE, "
        "previous_status VARCHAR(30), "
        "new_status VARCHAR(30) NOT NULL, "
        "changed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL, "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ");"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_order_status_history_order_id "
        "ON order_status_history (order_id);"
    )

    op.execute(
        "ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(36) "
        "REFERENCES users(id) ON DELETE SET NULL;"
    )
    op.execute(
        "ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS reviewed_at "
        "TIMESTAMP WITH TIME ZONE;"
    )
    op.execute(
        "ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS review_comment TEXT;"
    )

    op.execute(
        "CREATE TABLE IF NOT EXISTS return_request_history ("
        "id VARCHAR(36) PRIMARY KEY, "
        "return_request_id VARCHAR(36) NOT NULL REFERENCES return_requests(id) ON DELETE CASCADE, "
        "previous_status VARCHAR(20), "
        "new_status VARCHAR(20) NOT NULL, "
        "comment TEXT, "
        "changed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL, "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ");"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_return_request_history_return_request_id "
        "ON return_request_history (return_request_id);"
    )


def downgrade() -> None:
    # Intentionally non-destructive: order/return audit history and review
    # decisions are historical records that must not be discarded.
    pass
