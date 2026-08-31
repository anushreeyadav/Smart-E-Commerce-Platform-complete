DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'orderstatus') THEN
        ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'OUT_FOR_DELIVERY';
    END IF;
END $$;

ALTER TABLE orders ADD COLUMN IF NOT EXISTS shipping_address TEXT;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at
    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;

CREATE TABLE IF NOT EXISTS order_status_history (
    id VARCHAR(36) PRIMARY KEY,
    order_id VARCHAR(36) NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    previous_status VARCHAR(30),
    new_status VARCHAR(30) NOT NULL,
    changed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_order_status_history_order_id ON order_status_history (order_id);

ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(36)
    REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE return_requests ADD COLUMN IF NOT EXISTS review_comment TEXT;

CREATE TABLE IF NOT EXISTS return_request_history (
    id VARCHAR(36) PRIMARY KEY,
    return_request_id VARCHAR(36) NOT NULL REFERENCES return_requests(id) ON DELETE CASCADE,
    previous_status VARCHAR(20),
    new_status VARCHAR(20) NOT NULL,
    comment TEXT,
    changed_by VARCHAR(36) REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_return_request_history_return_request_id
    ON return_request_history (return_request_id);
