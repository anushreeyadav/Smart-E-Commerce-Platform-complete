-- Existing products remain active.  No product rows are changed or removed.
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS ix_products_is_active
    ON products (is_active);
