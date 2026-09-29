from __future__ import annotations

import json
import sys
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend_api"
for path in (ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backend_api.database import connect


VALID_MCI_OBLIGATION_IDS = [1381, 1382, 1385]
EXP_PROF_CODE = "500-001-001-006"
EXP_PROF_NAME = "Servicios Profesionales"
AP_CODE = "2.1.01.01"
AP_NAME = "Cuentas por pagar-comerciales"


def document_detail(payee_name: str, reference: str | None, obligation_id: int) -> str:
    payee = (payee_name or "").strip() or "N/A"
    ref = str(reference or "").strip()
    return f"{payee} Fac{ref}" if ref else f"{payee} ITP {obligation_id}"


def fetch_all(cur, query: str, params=None):
    cur.execute(query, params or ())
    return [dict(row) for row in cur.fetchall()]


def main() -> None:
    conn = connect()
    conn.autocommit = False
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            UPDATE payment_obligations
               SET notes = REPLACE(REPLACE(notes, 'obligaci�n', 'obligacion'), 'obligación', 'obligacion')
             WHERE id = ANY(%s)
            """,
            ([1363, 1375, 1368, 1381, 1382, 1385],),
        )

        cur.execute(
            """
            SELECT id, company_code, payee_name, reference, issue_date, total, status, active
            FROM payment_obligations
            WHERE id = ANY(%s)
              AND company_code = 'MCI-CR'
              AND currency = 'CRC'
              AND status = 'PENDING'
              AND active = TRUE
            ORDER BY id
            """,
            (VALID_MCI_OBLIGATION_IDS,),
        )
        obligations = cur.fetchall()

        for ob in obligations:
            obligation_id = int(ob["id"])
            issue_date = ob["issue_date"]
            period = issue_date.strftime("%Y-%m")
            total = float(ob["total"] or 0)
            detail = f"From ITP {document_detail(ob['payee_name'], ob['reference'], obligation_id)}"

            cur.execute(
                """
                DELETE FROM accounting_lines
                WHERE entry_id IN (
                    SELECT id
                    FROM accounting_entries
                    WHERE origin IN ('ITP', 'ITP_PAYMENT')
                      AND origin_id = %s
                      AND company_code = 'MCI-CR'
                )
                """,
                (obligation_id,),
            )
            cur.execute(
                """
                DELETE FROM accounting_entries
                WHERE origin IN ('ITP', 'ITP_PAYMENT')
                  AND origin_id = %s
                  AND company_code = 'MCI-CR'
                """,
                (obligation_id,),
            )
            cur.execute(
                """
                INSERT INTO accounting_entries (
                    company_code, entry_date, period, description, origin, origin_id, created_by
                )
                VALUES ('MCI-CR', %s, %s, %s, 'ITP', %s, 'SYSTEM')
                RETURNING id
                """,
                (issue_date, period, detail, obligation_id),
            )
            entry_id = cur.fetchone()["id"]
            cur.execute(
                """
                INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                VALUES
                    (%s, %s, %s, %s, 0, %s),
                    (%s, %s, %s, 0, %s, %s)
                """,
                (
                    entry_id,
                    EXP_PROF_CODE,
                    EXP_PROF_NAME,
                    total,
                    detail,
                    entry_id,
                    AP_CODE,
                    AP_NAME,
                    total,
                    detail,
                ),
            )

        conn.commit()

        verification = {
            "reposted_obligations": [dict(row) for row in obligations],
            "entries": fetch_all(
                cur,
                """
                SELECT e.id, e.company_code, e.origin, e.origin_id, e.entry_date,
                       e.description, l.id AS line_id, l.account_code, l.debit, l.credit
                FROM accounting_entries e
                JOIN accounting_lines l ON l.entry_id = e.id
                WHERE e.origin IN ('ITP', 'ITP_PAYMENT')
                  AND e.origin_id = ANY(%s)
                ORDER BY e.company_code, e.origin_id, e.origin, l.id
                """,
                ([1363, 1375, 1368, 1381, 1382, 1385],),
            ),
        }
        print(json.dumps(verification, default=str, ensure_ascii=False, indent=2))
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
