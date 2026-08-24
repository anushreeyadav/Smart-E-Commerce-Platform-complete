-- Notifications table for Smart E-Commerce
-- Apply this on an existing PostgreSQL database.

BEGIN;

DO $$
BEGIN
    CREATE TYPE notificationtype AS ENUM (
        'ORDER_CONFIRMED',
        'PAYMENT_SUCCESS',
        'PAYMENT_FAILED',
        'ORDER_SHIPPED',
        'ORDER_DELIVERED'
    );
EXCEPTION
    WHEN duplicate_object THEN
        NULL;
END $$;

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type notificationtype NOT NULL,
    message VARCHAR(500) NOT NULL,
    read_status BOOLEAN NOT NULL DEFAULT FALSE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_notifications_user_id
    ON notifications (user_id);

CREATE INDEX IF NOT EXISTS ix_notifications_read_status
    ON notifications (read_status);

CREATE INDEX IF NOT EXISTS ix_notifications_timestamp
    ON notifications (timestamp);

CREATE INDEX IF NOT EXISTS ix_notifications_user_timestamp
    ON notifications (user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS ix_notifications_user_read_status
    ON notifications (user_id, read_status);

COMMIT;
