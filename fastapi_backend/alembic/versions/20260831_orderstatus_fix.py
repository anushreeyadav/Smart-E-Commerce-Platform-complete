"""ensure orderstatus enum has every OrderStatus member

Revision ID: 20260831_orderstatus_fix
Revises: 20260831_return_req_fix
Create Date: 2026-08-31

Same drift pattern as 20260831_return_req_fix: on databases where the
`orderstatus` type pre-dates the app's OrderStatus enum, individual
values (observed: 'PAID') can be missing even though 'RETURN_REQUESTED'
was separately patched in. Add every member the model requires,
idempotently, so the transition chain
PENDING -> CONFIRMED -> PAID -> SHIPPED -> DELIVERED -> RETURN_REQUESTED
(and CANCELLED) always has a valid target value in the DB enum. No-op on
databases that already have all of these.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_orderstatus_fix"
down_revision: Union[str, Sequence[str], None] = "20260831_return_req_fix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

REQUIRED_VALUES = [
    "PENDING",
    "CONFIRMED",
    "PAID",
    "SHIPPED",
    "DELIVERED",
    "RETURN_REQUESTED",
    "CANCELLED",
]


def upgrade() -> None:
    for value in REQUIRED_VALUES:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
                    ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS '{value}';
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # Intentionally non-destructive: Postgres cannot drop individual enum
    # values without recreating the type, and existing order rows may use them.
    pass
