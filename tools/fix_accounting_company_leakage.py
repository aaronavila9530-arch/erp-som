from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from psycopg2.extras import RealDictCursor


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend_api"))

import database  # noqa: E402


ACCOUNT_COMPANIES = {
    "contabilidad@mslogisticsgroup.com": "MSL-CR",
    "gastos@mslogisticsgroup.com": "MSL-CR",
    "facturacion.fe@xtravon.com": "MCI-CR",
    "operations@xtravon.com": "MCI-CR",
}


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def fetch_all(cur, sql: str, params: tuple = ()) -> list[dict]:
    cur.execute(sql, params)
    return [dict(row) for row in cur.fetchall()]


def fetch_one(cur, sql: str, params: tuple = ()) -> dict:
    cur.execute(sql, params)
    row = cur.fetchone()
    return dict(row or {})


def account_values_sql() -> str:
    values = ",".join(["(%s,%s)"] * len(ACCOUNT_COMPANIES))
    return f"(VALUES {values}) AS account_map(account_email,target_company)"


def account_values_params() -> tuple:
    params: list[str] = []
    for email, company in ACCOUNT_COMPANIES.items():
        params.extend([email, company])
    return tuple(params)


def gmail_doc_target_cte() -> tuple[str, tuple]:
    mapping = account_values_sql()
    params = account_values_params()
    sql = f"""
        WITH target_docs AS (
            SELECT DISTINCT
                   d.id,
                   d.company_code,
                   account_map.target_company,
                   LOWER(m.account_email) AS account_email,
                   d.direction,
                   d.source_table,
                   d.source_id,
                   d.xml_hash,
                   d.electronic_key,
                   d.document_number
            FROM tax_electronic_documents d
            JOIN gmail_fiscal_attachments a ON a.tax_document_id = d.id
            JOIN gmail_fiscal_messages m ON m.id = a.message_id
            JOIN {mapping} ON account_map.account_email = LOWER(m.account_email)
            WHERE d.company_code <> account_map.target_company
        )
    """
    return sql, params


def ensure_connections(cur):
    for email in ACCOUNT_COMPANIES:
        cur.execute(
            """
            INSERT INTO gmail_fiscal_connections(account_email)
            VALUES(%s)
            ON CONFLICT(account_email) DO NOTHING
            """,
            (email,),
        )


def preview(cur) -> dict:
    cte, params = gmail_doc_target_cte()
    gmail_docs = fetch_all(
        cur,
        cte
        + """
        SELECT id, company_code, target_company, account_email, electronic_key, document_number
        FROM target_docs
        ORDER BY id
        LIMIT 25
        """,
        params,
    )
    gmail_counts = fetch_all(
        cur,
        cte
        + """
        SELECT company_code, target_company, account_email, COUNT(*) AS count
        FROM target_docs
        GROUP BY company_code, target_company, account_email
        ORDER BY account_email, company_code, target_company
        """,
        params,
    )
    conflicts = fetch_all(
        cur,
        cte
        + """
        SELECT td.id, td.company_code, td.target_company, td.account_email,
               td.electronic_key, td.xml_hash, td.source_table, td.source_id
        FROM target_docs td
        WHERE EXISTS (
                SELECT 1
                FROM tax_electronic_documents x
                WHERE x.id <> td.id
                  AND x.company_code = td.target_company
                  AND x.direction = td.direction
                  AND x.source_table = td.source_table
                  AND x.source_id = td.source_id
            )
           OR (
                td.xml_hash IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM tax_electronic_documents x
                    WHERE x.id <> td.id
                      AND x.company_code = td.target_company
                      AND x.direction = td.direction
                      AND x.xml_hash = td.xml_hash
                )
           )
        ORDER BY td.id
        LIMIT 25
        """,
        params,
    )
    obligation_counts = fetch_all(
        cur,
        cte
        + """
        SELECT p.company_code, td.target_company, COUNT(DISTINCT p.id) AS count
        FROM payment_obligations p
        JOIN target_docs td ON (
            (td.electronic_key IS NOT NULL AND td.electronic_key <> ''
             AND (p.electronic_key = td.electronic_key OR p.reference = td.electronic_key))
            OR
            (td.document_number IS NOT NULL AND td.document_number <> ''
             AND p.reference = td.document_number)
        )
        WHERE p.company_code <> td.target_company
        GROUP BY p.company_code, td.target_company
        ORDER BY p.company_code, td.target_company
        """,
        params,
    )
    itp_entry_counts = fetch_all(
        cur,
        """
        SELECT e.company_code, p.company_code AS target_company, e.origin, COUNT(*) AS count
        FROM accounting_entries e
        JOIN payment_obligations p ON p.id = e.origin_id
        WHERE e.origin IN ('ITP', 'ITP_PAYMENT')
          AND e.company_code <> p.company_code
        GROUP BY e.company_code, p.company_code, e.origin
        ORDER BY e.company_code, p.company_code, e.origin
        """,
    )
    cash_app_entry_counts = fetch_all(
        cur,
        """
        SELECT e.company_code, ca.company_code AS target_company, e.origin, COUNT(*) AS count
        FROM accounting_entries e
        JOIN cash_app ca ON ca.id = e.origin_id
        WHERE e.origin = 'CASH_APP'
          AND e.company_code <> ca.company_code
        GROUP BY e.company_code, ca.company_code, e.origin
        ORDER BY e.company_code, ca.company_code, e.origin
        """,
    )
    email_counts = fetch_all(
        cur,
        """
        SELECT LOWER(account_email) AS account_email, COUNT(*) AS messages
        FROM gmail_fiscal_messages
        GROUP BY LOWER(account_email)
        ORDER BY LOWER(account_email)
        """,
    )
    return {
        "gmail_document_mismatches": gmail_counts,
        "gmail_document_samples": gmail_docs,
        "gmail_document_conflict_samples": conflicts,
        "payment_obligation_mismatches_from_gmail_docs": obligation_counts,
        "itp_accounting_entry_mismatches": itp_entry_counts,
        "cash_app_accounting_entry_mismatches": cash_app_entry_counts,
        "gmail_message_accounts": email_counts,
    }


def apply(cur) -> dict:
    ensure_connections(cur)
    cte, params = gmail_doc_target_cte()
    moved_docs = fetch_all(
        cur,
        cte
        + """
        UPDATE tax_electronic_documents d
           SET company_code = td.target_company,
               updated_at = NOW()
          FROM target_docs td
         WHERE d.id = td.id
           AND NOT EXISTS (
                SELECT 1
                FROM tax_electronic_documents x
                WHERE x.id <> td.id
                  AND x.company_code = td.target_company
                  AND x.direction = td.direction
                  AND x.source_table = td.source_table
                  AND x.source_id = td.source_id
           )
           AND NOT (
                td.xml_hash IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM tax_electronic_documents x
                    WHERE x.id <> td.id
                      AND x.company_code = td.target_company
                      AND x.direction = td.direction
                      AND x.xml_hash = td.xml_hash
                )
           )
        RETURNING d.id, td.company_code AS old_company, d.company_code AS new_company, td.account_email
        """,
        params,
    )
    moved_obligations = fetch_all(
        cur,
        cte
        + """
        UPDATE payment_obligations p
           SET company_code = td.target_company
          FROM target_docs td
         WHERE p.company_code <> td.target_company
           AND (
                (td.electronic_key IS NOT NULL AND td.electronic_key <> ''
                 AND (p.electronic_key = td.electronic_key OR p.reference = td.electronic_key))
                OR
                (td.document_number IS NOT NULL AND td.document_number <> ''
                 AND p.reference = td.document_number)
           )
        RETURNING p.id, td.company_code AS document_old_company, p.company_code AS new_company, td.account_email
        """,
        params,
    )
    moved_entries = fetch_all(
        cur,
        """
        UPDATE accounting_entries e
           SET company_code = p.company_code,
               updated_at = NOW()
          FROM payment_obligations p
         WHERE e.origin IN ('ITP', 'ITP_PAYMENT')
           AND e.origin_id = p.id
           AND e.company_code <> p.company_code
        RETURNING e.id, e.origin, e.origin_id, e.company_code AS new_company
        """,
    )
    moved_cash_app_entries = fetch_all(
        cur,
        """
        UPDATE accounting_entries e
           SET company_code = ca.company_code,
               updated_at = NOW()
          FROM cash_app ca
         WHERE e.origin = 'CASH_APP'
           AND e.origin_id = ca.id
           AND e.company_code <> ca.company_code
        RETURNING e.id, e.origin, e.origin_id, e.company_code AS new_company
        """,
    )
    return {
        "tax_documents_moved": len(moved_docs),
        "payment_obligations_moved": len(moved_obligations),
        "accounting_entries_moved": len(moved_entries),
        "cash_app_accounting_entries_moved": len(moved_cash_app_entries),
        "tax_document_samples": moved_docs[:25],
        "payment_obligation_samples": moved_obligations[:25],
        "accounting_entry_samples": moved_entries[:25],
        "cash_app_accounting_entry_samples": moved_cash_app_entries[:25],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit/fix company leakage from Gmail fiscal into Accounting.")
    parser.add_argument("--apply", action="store_true", help="Apply fixes. Without this flag the script is read-only.")
    args = parser.parse_args()

    conn = database.get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            before = preview(cur)
            result = {"mode": "apply" if args.apply else "dry-run", "before": before}
            if args.apply:
                result["applied"] = apply(cur)
                result["after"] = preview(cur)
                conn.commit()
            else:
                conn.rollback()
            print(json.dumps(result, indent=2, default=_json_default, ensure_ascii=False))
    except Exception:
        conn.rollback()
        raise
    finally:
        database.release_conn(conn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
