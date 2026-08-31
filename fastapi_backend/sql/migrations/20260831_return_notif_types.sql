DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'RETURN_APPROVED';
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'RETURN_REJECTED';
    END IF;
END $$;
