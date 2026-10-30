"""Keep audited document adjustments stable during automatic accrual rebuilds."""
import re


def _document_number(value):
    digits = re.sub(r'\D', '', str(value or ''))
    return digits[21:41] if len(digits) == 50 else digits


def load_reconciled_documents(cur, direction, company=None):
    cur.execute("""
        SELECT e.company_code, a.snapshot
        FROM accounting_audit_log a
        JOIN accounting_entries e ON e.id = a.entry_id
        WHERE a.action = 'EXCEL_RECONCILE'
          AND e.workflow_status = 'POSTED' AND COALESCE(e.reversed,FALSE)=FALSE
          AND a.snapshot->>'direction' = %s
          AND (%s IS NULL OR e.company_code = %s)
    """, (direction, company, company))
    result=[]
    for row in cur.fetchall():
        snapshot=row.get('snapshot') or {}
        result.append((row['company_code'], snapshot))
    return result


def is_reconciled(documents, company, source_id, number, party=None):
    candidate=_document_number(number)
    for tenant, snapshot in documents:
        if tenant != company:
            continue
        if source_id in snapshot.get('source_ids', []):
            return True
        if not candidate or candidate != _document_number(snapshot.get('number')):
            continue
        if snapshot.get('direction') == 'SALE':
            return True
        # Purchase consecutives are not unique across suppliers.
        original=str(snapshot.get('party') or '').strip().casefold()
        if original and original == str(party or '').strip().casefold():
            return True
    return False
