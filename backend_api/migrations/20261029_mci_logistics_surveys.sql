BEGIN;
ALTER TABLE mci_generic_surveys DROP CONSTRAINT IF EXISTS mci_generic_surveys_kind_check;
ALTER TABLE mci_generic_surveys ADD CONSTRAINT mci_generic_surveys_kind_check
CHECK (kind IN ('vessel','condition','cargo','container','logistics'));
CREATE TABLE IF NOT EXISTS mci_logistics_imports (
    legacy_id INTEGER PRIMARY KEY,
    report_id BIGINT NOT NULL UNIQUE REFERENCES mci_generic_surveys(id),
    source_snapshot JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
