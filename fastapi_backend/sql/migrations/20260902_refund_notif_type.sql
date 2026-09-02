-- Adds the REFUND_PROCESSED notification type, sent when an admin refund
-- for an approved/returned return request is processed.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notificationtype') THEN
        ALTER TYPE notificationtype ADD VALUE IF NOT EXISTS 'REFUND_PROCESSED';
    END IF;
END $$;
