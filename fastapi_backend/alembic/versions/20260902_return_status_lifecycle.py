"""allow returned/refunded return request statuses

Revision ID: 20260902_return_status_lifecycle
Revises: 20260831_return_notif_types
Create Date: 2026-09-02

Extends the return_requests.status CHECK constraint so a return request can
progress past approval: pending -> approved|rejected -> returned -> refunded.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260902_return_status_lifecycle"
down_revision: Union[str, Sequence[str], None] = "20260831_return_notif_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_return_requests_status'
            ) THEN
                ALTER TABLE return_requests DROP CONSTRAINT ck_return_requests_status;
            END IF;

            ALTER TABLE return_requests
                ADD CONSTRAINT ck_return_requests_status
                CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'RETURNED', 'REFUNDED'));
        END $$;
        """
    )


def downgrade() -> None:
    # Intentionally non-destructive: existing rows may already use the new
    # statuses, and Postgres cannot restore the narrower constraint safely
    # without first migrating that data away.
    pass
