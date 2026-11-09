# Crane Inspections Web Audit

Date: 2026-11-09

## Scope and desktop baseline

Port Captancy was already available and verified through live bootstrap responses
for MSL and MCI. Per the requested fallback, this implementation adds Crane
Inspections under Informes > Buques, not under standalone Certificates.

Audited desktop form, table, presentation popup, PORTIA popup, legacy API payload,
Word and presentation exporters, and both retained DOCX templates.

The web MSL field set matches `FORM_ALLOWED_COLUMNS` excluding managed status:
service identity, dates and times, gear survey, 15 checklist points with performed
flag and four independent statuses, four cranes with ten remarks each, ten
recommendations, ten grabs observations, twenty conclusions and one picture link.

The current production table already contains all required desktop columns.
Two historical reports are Approved and linked to MSL. No MCI Crane history was
found. No historical reports are copied, edited, rejected or re-approved.

## Company isolation

- MSL uses the existing Crane table, scoped by an unambiguous Services company.
- MCI uses `mci_generic_surveys` and the existing MCI technical report templates.
- The additive kind constraint migration does not modify report rows.
- Report number, vessel, client and location come from the linked company service.
- MCI section and subsection checkboxes retain disabled text but exclude it from exports.
- Checklist data is structured and validates the same options as desktop.
- Create and Review remain separate. Editing, approval and export retain existing permissions.
- Duplicate creation is guarded by a transaction advisory lock. Updates reject stale
  versions, report relinking, and edits to Approved reports.

## Export and compatibility

MSL uses the original report and presentation templates in request-local files.
Original files and desktop code are unchanged. The web output corrects three
template mapping defects: missing fourth wire status, luffing-center statuses
incorrectly linked to cargo-block statuses, and duplicated seventh Crane 3 remark
in the ninth slot. Partially blank statuses no longer discard populated observations.

Web output retains header/footer artwork, uses dynamic page counts, keeps cover
text outside the photo strip and keeps signature text together. MCI uses the same
technical report design as its other reports, with Crane-specific optional groups.
Both support Word/PDF and ordered PDF annexes; MSL also supports presentation and
presentation plus report. PORTIA proposals require explicit acceptance and cannot
silently replace observations.

## Verification

- Unit tests: field parity, isolation, dates, booleans/options, limits, identity,
  duplicate handling, stale/approved protection, template hashes, all four statuses,
  corrected remark mapping, disabled sections and MCI export.
- Regression suite covers Port Captancy, MCI schemas/export/storage, certificates,
  Vessel fields, Logistics and Grain. Existing kiosk auth integration test is
  excluded from local regression because it opens an external DB connection.
- Browser fixtures exercise create/review, saving false checkboxes, fourth status,
  block limits, single picture link and 1440/800/390-pixel layouts.
- Local render review covers MSL report/cover and MCI report with multi-page text.
- Production verification must be read-only; no synthetic production reports.
