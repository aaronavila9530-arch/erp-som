# Port Captancy Web Audit

Date: 2026-11-02

## Desktop Contract

Reviewed the desktop form, table, PORTIA popup, PDF merge popup, API router,
Word generator, presentation generator and the three original DOCX templates.
The form has 82 persisted fields: service identity, introduction, arrival and
inspection timestamps, master/chief officer, vessel particulars, five time-sheet
events, three narrative groups of up to 15 items and one picture link.

The presentation generator selects steel for operations containing acero/steel
and grain otherwise. The desktop popup selection is not sent to that generator.
Web retains the generator's operation-based behavior rather than showing an
ineffective selector. MSL signature and imagery remain those of the original.

## Isolation

- No desktop Python modules, legacy API routes or original templates changed.
- MSL web reads and writes the existing table, scoped through a unique company
  derived from the linked Services report number. Ambiguous links fail closed.
- MCI uses its existing separate generic-report table, a new allowed kind and
  its existing letterhead/body layout with Port Captancy-specific fields.
- Production read-only audit found zero legacy Port Captancy reports.
- The migration only extends the MCI kind constraint; no report rows are changed.
- Report number, client, vessel and location derive from Services.
- Permission checks, approved-record lock and version conflict handling remain.
- Duplicate web creates are serialized with transaction advisory locks.

## Workflow And Exports

Create selects a service; Review lists existing reports. MSL has Word, report
PDF, presentation PDF and combined PDF. MCI uses its technical report Word/PDF.
Both accept ordered PDF annexes for download without persisting them.
PORTIA offers a proposal that must be explicitly accepted.
MCI checkboxes control sections and subsections; disabled text is retained but
excluded from exports. One picture URL, no repeated enclosure text boxes.

Web generation uses isolated temporary paths, preserves source template hashes,
repairs running-header references and keeps headings with their following text.
The MSL cover text is bounded away from the original photo strip.

## Validation

Unit coverage: field parity, company scope, service identity, invalid dates/times,
duplicate prevention, MCI section limits, hidden narrative, original-template
hash preservation, PDF annex validity and order. Regression suites include MCI
surveys, vessel fields, Logistics and certificate exports/permissions.
The legacy kiosk TestClient test was excluded after hanging in this environment;
no change to kiosk authentication is included here.

Playwright uses local mocked API responses, no production report writes, and
checks saving, PORTIA acceptance, section limits, single URL and horizontal
overflow at 1440, 800 and 390 pixels. Generated MSL steel/grain covers and both
report formats were converted with LibreOffice and visually inspected.
