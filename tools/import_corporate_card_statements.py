from __future__ import annotations

import argparse
from pathlib import Path

from psycopg2.extras import RealDictCursor

import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import get_conn, release_conn  # noqa: E402
from routers.corporate_cards import (  # noqa: E402
    _json_safe,
    ensure_schema,
    parse_bac_statement,
    post_history,
    HistoryPostRequest,
)


def _looks_like_card_statement(path: Path) -> bool:
    name = path.name.lower()
    return (
        "estadocta" in name
        or "estadodecuenta" in name
        or "estadocuenta" in name
        or "_extracto_" in name
    ) and path.suffix.lower() == ".pdf"


def _iter_files(paths: list[Path]):
    seen = set()
    for path in paths:
        if path.is_file():
            candidates = [path]
        else:
            candidates = [item for item in path.rglob("*.pdf") if _looks_like_card_statement(item)]
        for item in candidates:
            key = str(item.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            yield item


def import_file(cur, path: Path, company: str) -> tuple[str, str]:
    raw = path.read_bytes()
    parsed = parse_bac_statement(raw)
    period = parsed.get("statement_period")
    if not period or not (period.startswith("2025-") or period.startswith("2026-")):
        return "SKIPPED", f"{path.name}: periodo fuera de 2025-2026"
    import hashlib
    from psycopg2.extras import Json

    digest = hashlib.sha256(raw).hexdigest()
    cur.execute("SELECT id FROM corporate_card_statements WHERE file_hash=%s", (digest,))
    if cur.fetchone():
        return "DUPLICATE", f"{path.name}: ya importado"
    cur.execute("""
        INSERT INTO corporate_card_statements(
            company_code, bank_name, card_last4, statement_period, cutoff_date,
            payment_due_date, cash_payment_crc, cash_payment_usd, source_filename,
            file_hash, raw_text, parsed_payload, imported_by
        ) VALUES(%s,'BAC',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'LOCAL_TOOL')
        RETURNING id
    """, (
        company, parsed.get("card_last4"), period, parsed.get("cutoff_date"),
        parsed.get("payment_due_date"), parsed.get("cash_payment_crc"), parsed.get("cash_payment_usd"),
        str(path), digest, parsed.get("raw_text"), Json(_json_safe(parsed)),
    ))
    statement_id = cur.fetchone()["id"]
    inserted = 0
    for tx in parsed.get("transactions") or []:
        cur.execute("""
            INSERT INTO corporate_card_transactions(
                statement_id, company_code, card_last4, user_name, transaction_type,
                reference, transaction_date, description, merchant, currency,
                amount_original, amount_crc, fiscal_category, deductible_status,
                requires_invoice, expense_account_code, expense_account_name
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(statement_id, reference, transaction_date, amount_original, currency) DO NOTHING
        """, (
            statement_id, company, tx.get("card_last4"), tx.get("user_name"), tx.get("transaction_type"),
            tx.get("reference"), tx.get("transaction_date"), tx.get("description"), tx.get("merchant"),
            tx.get("currency"), tx.get("amount_original"), tx.get("amount_crc"),
            "SIN_CLASIFICAR", "PENDING_REVIEW", tx.get("transaction_type") == "PURCHASE",
            None, None,
        ))
        inserted += cur.rowcount
    return "IMPORTED", f"{path.name}: {period} tarjeta {parsed.get('card_last4')} movimientos {inserted}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Archivos o carpetas con estados BAC PDF")
    parser.add_argument("--company", default="MSL-CR")
    parser.add_argument("--post-history", action="store_true")
    args = parser.parse_args()

    conn = get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ensure_schema(cur)
            counts = {"IMPORTED": 0, "DUPLICATE": 0, "SKIPPED": 0, "ERROR": 0}
            for path in _iter_files([Path(item) for item in args.paths]):
                try:
                    status, message = import_file(cur, path, args.company)
                    counts[status] = counts.get(status, 0) + 1
                    print(status, message)
                except Exception as exc:
                    counts["ERROR"] += 1
                    print("ERROR", f"{path}: {exc}")
            conn.commit()
        print("SUMMARY", counts)
    finally:
        release_conn(conn)

    if args.post_history:
        conn = get_conn()
        try:
            result = post_history(
                HistoryPostRequest(years=[2025, 2026], settle_previous=True, leave_latest_pending=True, latest_pending_per_card=True),
                x_company_code=args.company,
                conn=conn,
            )
            print("POST_HISTORY", result)
        finally:
            release_conn(conn)


if __name__ == "__main__":
    main()
