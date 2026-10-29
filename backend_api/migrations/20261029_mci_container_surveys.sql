BEGIN;
ALTER TABLE mci_generic_surveys DROP CONSTRAINT IF EXISTS mci_generic_surveys_kind_check;
ALTER TABLE mci_generic_surveys ADD CONSTRAINT mci_generic_surveys_kind_check
    CHECK (kind IN ('vessel','condition','cargo','container'));
CREATE TABLE IF NOT EXISTS mci_survey_sources (
    report_id BIGINT PRIMARY KEY REFERENCES mci_generic_surveys(id),
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    document BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
COMMIT;
