-- Extends the return_requests.status CHECK constraint so a return request
-- can progress past approval: pending -> approved|rejected -> returned -> refunded.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'ck_return_requests_status'
    ) THEN
        ALTER TABLE return_requests DROP CONSTRAINT ck_return_requests_status;
    END IF;

    ALTER TABLE return_requests
        ADD CONSTRAINT ck_return_requests_status
        CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'RETURNED', 'REFUNDED'));
END $$;
