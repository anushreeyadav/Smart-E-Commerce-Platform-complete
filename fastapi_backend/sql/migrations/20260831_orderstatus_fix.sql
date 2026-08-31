-- Ensures the orderstatus enum has every OrderStatus member. Same drift
-- pattern as 20260831_return_request_schema_fix.sql: on databases where the
-- orderstatus type pre-dates the app's OrderStatus enum, individual values
-- (observed: 'PAID') can be missing even after 'RETURN_REQUESTED' was
-- patched in separately. No-op on databases that already have all of these.

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'PENDING';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'CONFIRMED';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'PAID';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'SHIPPED';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'DELIVERED';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'RETURN_REQUESTED';
    END IF;
END $$;

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'CANCELLED';
    END IF;
END $$;
