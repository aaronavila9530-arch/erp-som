# Logistics Supervision web audit

Date: 2026-10-29

## Desktop source of truth

The desktop label is Logistics Supervision; implementation uses vessel_truck_supervision.
Audited create/review form, review popup, table, final-report popup, legacy router,
Word service, PDF service and presentation service. The 21 editable database fields
are mirrored by services/logistics_web_fields.py. No calculations or truck-row
ledger exist in this report: process, documentary findings, operational findings,
incidents and conclusion are narrative fields.

MSL uses vessel_truck_supervision_aligned_dates.docx and
presentation_truck_supervision.docx. Fixed references to corn/soy, El Surco,
Puerto Caldera, attachments and Pabel Pena are retained. Source files are not
rewritten. Generated web copies keep headings with following text and constrain
cover text away from the right-hand photographs. Word, PDF, presentation and
combined PDF are independent of approval. Blank dates stay blank, rather than
silently deriving a date from a report number.

## Isolation and compatibility

No desktop module, legacy route or desktop generator is changed. MSL web uses the
same existing table with bounded fields, service-derived identity, company scope,
duplicate checks and optimistic conflict detection. Report ownership is resolved
through an unambiguous Services link, not an old table default. Approving/rejecting
MSL Logistics updates the linked service status for that company only.

MCI uses the existing generic narrative editor and letterhead, with specific vessel
particulars, time sheet, supervision process, documentary findings, operational
control findings and incidents. Parent/child checkboxes control exports without
deleting disabled text. Picture link remains a single input. Number, vessel,
customer and location are service-derived. No fixed commodity, client-specific
procedures or signatory are invented. Existing generic report kinds retain their
section contracts. PORTIA offers a proposal requiring acceptance, never autosaves.

## Historical data

Read-only audit found 12 desktop reports: eight linked to MSL and four linked to
MCI despite an MSL default in their legacy company column. User authorized copying
the four MCI records (legacy IDs 9, 22, 23, 24) as Draft into the new MCI format.
The import is idempotent, validates the exact source set, retains a source JSON
snapshot and mapping, and verifies original rows and statuses are unchanged.
No legacy records are deleted, relabeled or approved by the import.

## Verification scope

Unit tests cover exact fields, tenant boundaries, duplicate prevention, dates,
identity, narrative migration, parent/child export suppression and template hashes.
Browser tests cover both companies, responsive widths, editing, saving, section
controls, exports and mocked PORTIA proposal acceptance. QA documents are rendered
through LibreOffice for inspection. Production checks use GET only after deploy;
no synthetic services or reports are posted. Desktop historical risks in its old
unscoped write routes are outside this web change and were not silently refactored.
