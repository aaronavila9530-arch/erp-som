from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend_api"
for path in (ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from backend_api.database import connect
from backend_api.services.accounting_auto import sync_itp_to_accounting


BAD_MSL_OBLIGATION_IDS = [1363, 1375, 1368]
VALID_MCI_OBLIGATION_IDS = [1382, 1381, 1385]
ALL_OBLIGATION_IDS = BAD_MSL_OBLIGATION_IDS + VALID_MCI_OBLIGATION_IDS


def fetch_all(cur, query: str, params=None):
    cur.execute(query, params or ())
    return [dict(row) for row in cur.fetchall()]


def main() -> None:
    conn = connect()
    conn.autocommit = False
    backup_path = (
        ROOT
        / "data_repair_backups"
        / f"itp_surveyor_autocutoff_company_currency_{datetime.now():%Y%m%d_%H%M%S}.json"
    )

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        backup = {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "reason": "Repair Costa Rica surveyor service obligations incorrectly duplicated across companies, stored as USD, and marked paid by AUTO-CUTOFF-2026-09.",
            "obligations": fetch_all(
                cur,
                """
                SELECT *
                FROM payment_obligations
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (ALL_OBLIGATION_IDS,),
            ),
            "entries": fetch_all(
                cur,
                """
                SELECT *
                FROM accounting_entries
                WHERE origin IN ('ITP', 'ITP_PAYMENT')
                  AND origin_id = ANY(%s)
                ORDER BY id
                """,
                (ALL_OBLIGATION_IDS,),
            ),
            "lines": fetch_all(
                cur,
                """
                SELECT l.*
                FROM accounting_lines l
                JOIN accounting_entries e ON e.id = l.entry_id
                WHERE e.origin IN ('ITP', 'ITP_PAYMENT')
                  AND e.origin_id = ANY(%s)
                ORDER BY l.id
                """,
                (ALL_OBLIGATION_IDS,),
            ),
            "services": fetch_all(
                cur,
                """
                SELECT *
                FROM servicios
                WHERE consec IN (491, 498, 504)
                ORDER BY consec
                """,
            ),
        }

        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(json.dumps(backup, default=str, ensure_ascii=False, indent=2), encoding="utf-8")

        cur.execute(
            """
            DELETE FROM accounting_lines
            WHERE entry_id IN (
                SELECT id
                FROM accounting_entries
                WHERE origin IN ('ITP', 'ITP_PAYMENT')
                  AND origin_id = ANY(%s)
            )
            """,
            (ALL_OBLIGATION_IDS,),
        )
        deleted_lines = cur.rowcount

        cur.execute(
            """
            DELETE FROM accounting_entries
            WHERE origin IN ('ITP', 'ITP_PAYMENT')
              AND origin_id = ANY(%s)
            """,
            (ALL_OBLIGATION_IDS,),
        )
        deleted_entries = cur.rowcount

        cur.execute(
            """
            UPDATE payment_obligations po
               SET active = FALSE,
                   status = 'REPLACED',
                   balance = 0,
                   last_payment_date = NULL,
                   payment_reference = NULL,
                   payment_bank = NULL,
                   payment_bank_account_code = NULL,
                   payment_bank_account_name = NULL,
                   notes = TRIM(BOTH E'\n' FROM CONCAT_WS(
                       E'\n',
                       NULLIF(po.notes, ''),
                       'Anulada por saneamiento: obligación duplicada en MSL para servicio perteneciente a MCI.'
                   )),
                   updated_at = NOW()
             WHERE po.id = ANY(%s)
            """,
            (BAD_MSL_OBLIGATION_IDS,),
        )
        replaced_msl = cur.rowcount

        cur.execute(
            """
            UPDATE payment_obligations po
               SET currency = 'CRC',
                   total = COALESCE(s.honorarios, po.total),
                   balance = COALESCE(s.honorarios, po.total),
                   status = 'PENDING',
                   last_payment_date = NULL,
                   payment_reference = NULL,
                   payment_bank = NULL,
                   payment_bank_account_code = NULL,
                   payment_bank_account_name = NULL,
                   notes = TRIM(BOTH E'\n' FROM CONCAT_WS(
                       E'\n',
                       NULLIF(regexp_replace(COALESCE(po.notes, ''), 'Marcado como pagado por saneamiento masivo septiembre 2026 hacia atras; excluye obligaciones quincenales pendientes\\.?', '', 'gi'), ''),
                       'Corregida por saneamiento: honorario Costa Rica en CRC y no pagado por banco.'
                   )),
                   updated_at = NOW()
              FROM servicios s
             WHERE po.id = ANY(%s)
               AND po.service_id = s.consec
               AND s.company_code = 'MCI-CR'
            """,
            (VALID_MCI_OBLIGATION_IDS,),
        )
        corrected_mci = cur.rowcount

        conn.commit()
        cur.close()

        sync_itp_to_accounting(conn, "MCI-CR")
        sync_itp_to_accounting(conn, "MSL-CR")

        verify_cur = conn.cursor(cursor_factory=RealDictCursor)
        verification = {
            "backup_path": str(backup_path),
            "deleted_lines": deleted_lines,
            "deleted_entries": deleted_entries,
            "replaced_msl_obligations": replaced_msl,
            "corrected_mci_obligations": corrected_mci,
            "obligations": fetch_all(
                verify_cur,
                """
                SELECT id, company_code, payee_name, reference, service_id, country,
                       currency, total, balance, status, active, payment_reference,
                       last_payment_date, updated_at
                FROM payment_obligations
                WHERE id = ANY(%s)
                ORDER BY id
                """,
                (ALL_OBLIGATION_IDS,),
            ),
            "entries": fetch_all(
                verify_cur,
                """
                SELECT e.id, e.company_code, e.origin, e.origin_id, e.entry_date,
                       e.description, l.id AS line_id, l.account_code, l.debit, l.credit
                FROM accounting_entries e
                JOIN accounting_lines l ON l.entry_id = e.id
                WHERE e.origin IN ('ITP', 'ITP_PAYMENT')
                  AND e.origin_id = ANY(%s)
                ORDER BY e.company_code, e.origin_id, e.origin, l.id
                """,
                (ALL_OBLIGATION_IDS,),
            ),
        }
        verify_cur.close()
        print(json.dumps(verification, default=str, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
