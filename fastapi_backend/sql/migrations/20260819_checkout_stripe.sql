-- Checkout + Stripe payment schema updates for Smart E-Commerce
-- Apply this on an existing PostgreSQL database.

BEGIN;

ALTER TABLE orders
    ADD COLUMN IF NOT EXISTS payment_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'usd',
    ADD COLUMN IF NOT EXISTS stripe_checkout_session_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS stripe_payment_intent_id VARCHAR(120);

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50) NOT NULL DEFAULT 'stripe';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_type
        WHERE typname = 'orderstatus'
    ) THEN
        BEGIN
            ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'confirmed';
        EXCEPTION
            WHEN duplicate_object THEN
                NULL;
        END;

        BEGIN
            ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'paid';
        EXCEPTION
            WHEN duplicate_object THEN
                NULL;
        END;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_stripe_checkout_session_id
    ON orders (stripe_checkout_session_id)
    WHERE stripe_checkout_session_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_stripe_payment_intent_id
    ON orders (stripe_payment_intent_id)
    WHERE stripe_payment_intent_id IS NOT NULL;

COMMIT;
