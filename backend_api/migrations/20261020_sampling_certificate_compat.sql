-- Additive desktop/web compatibility only. Existing rows remain untouched.
BEGIN;
SET LOCAL lock_timeout = '5s';
ALTER TABLE sampling_certificates
    ADD COLUMN IF NOT EXISTS holds_inspected text,
    ADD COLUMN IF NOT EXISTS observations text,
    ADD COLUMN IF NOT EXISTS closing_date text,
    ADD COLUMN IF NOT EXISTS closing_time text,
    ADD COLUMN IF NOT EXISTS master text;
COMMIT;
