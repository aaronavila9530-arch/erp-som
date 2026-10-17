# PORTIA: desktop audit and web implementation

## Existing desktop behavior

- `Modulos/Portia/portia_ui.py`: threaded requests, context refresh, suggested questions, single answer area, ERP/manual/general modes.
- `api_client.py`: calls `/portia/context` and `/portia/ask`, with local fallback when the server is unavailable.
- `ai/som_portia.py`: OpenAI completion or keyword-based fallback; no conversation history. The ERP fallback selects one topic rather than answering compound questions.
- `services/som_portia_context.py`: global, unfiltered aggregate queries. Missing sources can be converted to empty data/zero; currencies are not separated. This legacy builder is no longer used by the PORTIA HTTP routes.
- SOM WEB previously routed PORTIA to the generic coming-soon screen.

## New web behavior

- Dedicated conversation/evidence workspace; follow-ups, multiple questions, manual/general modes, dates and two fortnight shortcuts.
- Read-only curated SQL, no generated SQL or mutation tools. Company predicates on every business source. Module permission checks before finance/service queries; saved payroll lines additionally require administrative HHRR access.
- Separate currencies and concepts: posted expense ledger, issued invoices net of credit notes, supplier/payment obligations, current scheduled balances, saved fortnight batches, service activity.
- Invoice geography is attached only when the linked report has an unambiguous location. Unmapped invoices remain explicit, without duplicating amounts through joins.
- Current period compared with immediately preceding equal-length period. Current pending balances are not described as historical balance snapshots.
- All source totals calculated before displaying at most 50 groups/details. Sources exceeding 20,000 rows are omitted with a warning rather than reporting truncated totals. Query timeout: 8 seconds.
- Provider failure explicitly reported; deterministic multi-topic fallback remains available. Missing sources are never described as zero. No bank-account details, passwords or mailbox content included in model context.
- Conversation kept in memory, cleared on company/scope/date changes. Browser rendering uses escaped text; CSV formula prefixes escaped.

## Verification and limitations

- Unit tests: company predicates, permission exclusion, date/history validation, multi-question fallback, source failure behavior, decimal arithmetic and previous-period differences.
- Browser tests: follow-up history, multiple questions, scope reset, unsafe labels, desktop/mobile layouts.
- No live internet retrieval. Natural-language dates do not silently override selected dates.
- Fortnight sources include applied lines and latest saved draft only. Unsaved ITP projections are not manufactured; opening PORTIA never invokes ITP generators that can mutate state.
- Existing desktop binaries may show N/D for obsolete summary-card fields; answer/context payloads remain valid but use the new evidence structure. No desktop release is produced by this web change.
- Uses existing SOM identity/permission infrastructure. This change is not a replacement for the broader session-authentication architecture.
