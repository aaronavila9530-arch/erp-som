BEGIN;
ALTER TABLE mci_generic_surveys DROP CONSTRAINT IF EXISTS mci_generic_surveys_kind_check;
ALTER TABLE mci_generic_surveys ADD CONSTRAINT mci_generic_surveys_kind_check
CHECK (kind IN ('vessel','condition','cargo','container','logistics','port_captancy'));
COMMIT;
