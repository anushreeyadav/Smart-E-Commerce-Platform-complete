-- Reconciles databases where return_requests / orderstatus pre-date the
-- 20260831_return_requests migration (see that migration's IF NOT EXISTS
-- guards). No-op on databases where that migration applied cleanly.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'RETURN_REQUESTED';
    END IF;
END $$;

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
