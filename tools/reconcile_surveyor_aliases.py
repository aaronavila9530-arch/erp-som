from __future__ import annotations

import sys
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend_api import database
from backend_api.services.itp_surveyor_reconciliation import reconcile_surveyor_invoice_obligations


def main() -> None:
    conn = database.connect()
    total_matches: dict[str, list[int]] = {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, company_code, payee_name, issue_date, reference
                FROM payment_obligations
                WHERE COALESCE(active, TRUE)=TRUE
                  AND obligation_type='SUPPLIER_INVOICE'
                  AND COALESCE(payee_name,'') <> ''
                  AND company_code IN ('MSL-CR','MCI-CR')
                ORDER BY company_code, issue_date, id
                """
            )
            invoices = cur.fetchall() or []
            for invoice in invoices:
                matched = reconcile_surveyor_invoice_obligations(
                    cur,
                    invoice["company_code"],
                    invoice["payee_name"],
                    invoice["issue_date"],
                    reference=invoice.get("reference"),
                    invoice_obligation_id=invoice["id"],
                )
                if matched:
                    total_matches.setdefault(invoice["company_code"], []).extend(matched)
                    print(
                        f"{invoice['company_code']} invoice {invoice['id']} "
                        f"{invoice['payee_name']} -> replaced {matched}"
                    )
        conn.commit()
    finally:
        conn.close()

    if not total_matches:
        print("No surveyor alias obligations needed reconciliation.")
        return
    for company, ids in sorted(total_matches.items()):
        unique_ids = sorted(set(ids))
        print(f"{company}: {len(unique_ids)} obligation(s) reconciled: {unique_ids}")


if __name__ == "__main__":
    main()
