"""add return requests and order delivery timestamp

Revision ID: 20260831_return_requests
Revises: 20260826_product_activation
Create Date: 2026-08-31
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_return_requests"
down_revision: Union[str, Sequence[str], None] = "20260826_product_activation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
                ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'RETURN_REQUESTED';
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP WITH TIME ZONE;")
    op.execute(
        "CREATE TABLE IF NOT EXISTS return_requests ("
        "id VARCHAR(36) PRIMARY KEY, order_id VARCHAR(36) NOT NULL UNIQUE REFERENCES orders(id) ON DELETE CASCADE, "
        "user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE, reason VARCHAR(500) NOT NULL, "
        "comments TEXT, status VARCHAR(20) NOT NULL DEFAULT 'PENDING', "
        "CONSTRAINT ck_return_requests_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED')), "
        "created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, "
        "updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP"
        ");"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_return_requests_user_id ON return_requests (user_id);")


def downgrade() -> None:
    # Intentionally non-destructive: return-request records are customer history.
    pass
