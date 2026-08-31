"""reconcile return_requests schema on databases where it pre-dates the migration

Revision ID: 20260831_return_req_fix
Revises: 20260831_return_requests
Create Date: 2026-08-31

Some environments already had a `return_requests` table and/or `orderstatus`
type from an earlier prototype (created via SQLAlchemy's
Base.metadata.create_all with a native Postgres enum) before the
20260831_return_requests migration existed. Because that migration uses
`CREATE TABLE IF NOT EXISTS` / `ADD VALUE IF NOT EXISTS` guards, it silently
no-ops on those databases instead of reconciling the drift, leaving
`orders.status` without 'RETURN_REQUESTED' and `return_requests.status`
as a native enum missing 'APPROVED'/'REJECTED', with no UNIQUE constraint
on `order_id`. This migration brings any such database in line with the
intended schema. It is a no-op on databases where 20260831_return_requests
already applied cleanly.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "20260831_return_req_fix"
down_revision: Union[str, Sequence[str], None] = "20260831_return_requests"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Belt-and-suspenders: make sure RETURN_REQUESTED is present regardless of
    # whether the prior migration's ADD VALUE actually took effect here.
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

    # If return_requests.status is still the leftover native enum from an
    # earlier prototype (rather than the VARCHAR the model/migration intend),
    # convert it in place, preserving existing data.
    op.execute(
        """
        DO $$
        DECLARE
            col_type text;
        BEGIN
            SELECT udt_name INTO col_type
            FROM information_schema.columns
            WHERE table_name = 'return_requests' AND column_name = 'status';

            IF col_type IS NOT NULL AND col_type <> 'varchar' THEN
                ALTER TABLE return_requests ALTER COLUMN status DROP DEFAULT;
                ALTER TABLE return_requests
                    ALTER COLUMN status TYPE VARCHAR(20) USING status::text;
                ALTER TABLE return_requests ALTER COLUMN status SET DEFAULT 'PENDING';
            END IF;
        END $$;
        """
    )

    # Drop the leftover native enum type once nothing references it any more.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'returnrequeststatus')
               AND NOT EXISTS (
                   SELECT 1
                   FROM pg_attribute a
                   JOIN pg_type t ON t.oid = a.atttypid
                   WHERE t.typname = 'returnrequeststatus'
                     AND a.attnum > 0
                     AND NOT a.attisdropped
               )
            THEN
                DROP TYPE returnrequeststatus;
            END IF;
        END $$;
        """
    )

    # Ensure the status CHECK constraint exists (it never got created on
    # databases where the table pre-existed).
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_return_requests_status'
            ) THEN
                ALTER TABLE return_requests
                    ADD CONSTRAINT ck_return_requests_status
                    CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED'));
            END IF;
        END $$;
        """
    )

    # Ensure order_id is UNIQUE (one return request per order) — also never
    # got created on databases where the table pre-existed.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint con
                WHERE con.conrelid = 'return_requests'::regclass
                  AND con.contype = 'u'
                  AND con.conkey = ARRAY[
                      (SELECT attnum FROM pg_attribute
                       WHERE attrelid = 'return_requests'::regclass
                         AND attname = 'order_id')
                  ]
            ) THEN
                ALTER TABLE return_requests
                    ADD CONSTRAINT uq_return_requests_order_id UNIQUE (order_id);
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Intentionally non-destructive: return-request records are customer history.
    pass
