from __future__ import annotations

import argparse
import sys
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from database import get_conn, release_conn  # noqa: E402
from routers.corporate_cards import (  # noqa: E402
    apply_card_merchant_classification,
    classify_card_merchant,
    ensure_schema,
    _post_card_transaction,
)


def audit(company: str, apply: bool = False) -> dict:
    conn = get_conn()
    summary = {
        "company": company,
        "apply": apply,
        "matched_rules": 0,
        "updated_transactions": 0,
        "reposted_entries": 0,
        "skipped_matched_itp": 0,
        "errors": [],
        "by_account": {},
    }
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            ensure_schema(cur)
            cur.execute(
                """
                SELECT *
                FROM corporate_card_transactions
                WHERE company_code=%s
                  AND transaction_type='PURCHASE'
                  AND transaction_date >= DATE '2025-01-01'
                  AND transaction_date < DATE '2027-01-01'
                ORDER BY transaction_date, id
                """,
                (company,),
            )
            rows = [dict(row) for row in cur.fetchall() or []]
            for tx in rows:
                rule = classify_card_merchant(tx.get("merchant"), tx.get("description"), tx.get("notes"))
                if not rule:
                    continue
                classified = apply_card_merchant_classification(tx)
                account_code = rule["expense_account_code"]
                account_name = rule["expense_account_name"]
                summary["matched_rules"] += 1
                label = f"{account_code} {account_name}"
                summary["by_account"][label] = summary["by_account"].get(label, 0) + 1
                changed = (
                    tx.get("expense_account_code") != account_code
                    or tx.get("expense_account_name") != account_name
                    or (tx.get("fiscal_category") or "") != (classified.get("fiscal_category") or "")
                    or (tx.get("deductible_status") or "") != (classified.get("deductible_status") or "")
                    or bool(tx.get("requires_invoice")) != bool(classified.get("requires_invoice"))
                )
                if not apply:
                    continue
                if changed:
                    cur.execute(
                        """
                        UPDATE corporate_card_transactions
                        SET fiscal_category=%s,
                            deductible_status=%s,
                            requires_invoice=%s,
                            expense_account_code=%s,
                            expense_account_name=%s
                        WHERE id=%s
                        """,
                        (
                            classified.get("fiscal_category"),
                            classified.get("deductible_status") or "DEDUCTIBLE",
                            bool(classified.get("requires_invoice")),
                            account_code,
                            account_name,
                            tx["id"],
                        ),
                    )
                    summary["updated_transactions"] += cur.rowcount
                if tx.get("matched_obligation_id"):
                    summary["skipped_matched_itp"] += 1
                    continue
                try:
                    _post_card_transaction(cur, classified, force_closed_period=True)
                    summary["reposted_entries"] += 1
                except Exception as exc:
                    summary["errors"].append(f"tx {tx.get('id')}: {exc}")
            if apply:
                conn.commit()
            else:
                conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_conn(conn)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--company", default="MSL-CR")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = audit(args.company, apply=args.apply)
    print(result)


if __name__ == "__main__":
    main()
