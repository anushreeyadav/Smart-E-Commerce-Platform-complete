-- The store now only checks out in INR and product prices were always
-- entered as rupee amounts, never USD, so this is a relabel only —
-- total_amount figures are untouched, no FX conversion applied.
UPDATE orders SET currency = 'inr' WHERE currency <> 'inr';
