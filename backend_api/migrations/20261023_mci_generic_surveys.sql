BEGIN;
CREATE TABLE IF NOT EXISTS mci_generic_surveys (
    id BIGSERIAL PRIMARY KEY,
    company_code TEXT NOT NULL CHECK (company_code = 'MCI-CR'),
    kind TEXT NOT NULL CHECK (kind IN ('vessel','condition','cargo')),
    service_id BIGINT NOT NULL,
    report_number TEXT NOT NULL,
    vessel TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'Draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS mci_generic_surveys_lookup ON mci_generic_surveys(company_code, kind, id DESC);
COMMIT;
