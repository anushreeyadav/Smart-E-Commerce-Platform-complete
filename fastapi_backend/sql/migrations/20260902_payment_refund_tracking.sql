-- Tracks the Stripe refund id (and when it completed) on the payment
-- record, so a processed refund is traceable back to the exact Stripe
-- object that moved the money, not just inferred from payment.status.

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS stripe_refund_id VARCHAR(120),
    ADD COLUMN IF NOT EXISTS refunded_at TIMESTAMP WITH TIME ZONE;

CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_stripe_refund_id
    ON payments (stripe_refund_id)
    WHERE stripe_refund_id IS NOT NULL;
