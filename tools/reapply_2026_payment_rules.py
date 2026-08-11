from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from psycopg2.extras import RealDictCursor

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
sys.path.insert(0, str(BACKEND))

import database  # noqa: E402
from services.accounting_bank_rules import (  # noqa: E402
    BCR_COLLECTION_FEE_USD,
    external_surveyor_settlement,
    resolve_collections_bank,
    resolve_itp_bank,
    should_apply_bcr_collection_fee,
)


YEAR = 2026
COMPANY_CODE = "MSL-CR"
REPORT_DIR = ROOT / "reports" / "migrations"


def money(value) -> Decimal:
    try:
        return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def as_float(value) -> float:
    return float(money(value))


def to_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def period_for(value) -> str:
    value = to_date(value)
    return value.strftime("%Y-%m")


def rows_to_json(rows):
    def convert(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        return value

    return [{key: convert(value) for key, value in dict(row).items()} for row in rows]


def exchange_rate_for(cur, value) -> Decimal:
    value = to_date(value)
    cur.execute("SELECT rate FROM exchange_rate WHERE rate_date = %s LIMIT 1", (value,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT rate FROM exchange_rate ORDER BY rate_date DESC LIMIT 1")
        row = cur.fetchone()
    if not row:
        raise RuntimeError("No existe ningun tipo de cambio registrado.")
    return money(row["rate"])


def latest_exchange_rate(cur) -> Decimal:
    cur.execute("""
        SELECT rate
        FROM exchange_rate
        WHERE rate_date <= CURRENT_DATE
        ORDER BY rate_date DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        raise RuntimeError("No existe ningun tipo de cambio registrado.")
    return money(row["rate"])


def ensure_accounting_schemas(cur):
    cur.execute("ALTER TABLE cash_app ADD COLUMN IF NOT EXISTS bank_account_code TEXT")
    cur.execute("ALTER TABLE cash_app ADD COLUMN IF NOT EXISTS bank_account_name TEXT")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank TEXT")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank_account_code TEXT")
    cur.execute("ALTER TABLE payment_obligations ADD COLUMN IF NOT EXISTS payment_bank_account_name TEXT")


def account_exists(cur, code: str) -> bool:
    cur.execute(
        "SELECT 1 FROM accounting_ledger WHERE account_code = %s AND COALESCE(active, TRUE) = TRUE LIMIT 1",
        (code,),
    )
    return cur.fetchone() is not None


def ensure_account(cur, code: str, name: str, account_type: str, normal_balance: str, parent_account=None):
    cur.execute("""
        UPDATE accounting_ledger
           SET account_name = %s,
               account_type = %s,
               account_level = COALESCE(account_level, %s),
               parent_account = COALESCE(parent_account, %s),
               active = TRUE
         WHERE account_code = %s
    """, (name, account_type, 4, parent_account, code))
    cur.execute("""
        INSERT INTO accounting_ledger (
            account_code, account_name, account_type, account_level, parent_account, active
        )
        SELECT %s, %s, %s, %s, %s, TRUE
        WHERE NOT EXISTS (
            SELECT 1 FROM accounting_ledger WHERE account_code = %s
        )
    """, (code, name, account_type, 4, parent_account, code))
    cur.execute("""
        UPDATE accounting_accounts
           SET account_name = %s,
               account_type = %s,
               normal_balance = %s,
               parent_account = COALESCE(parent_account, %s),
               active = TRUE,
               accepts_posting = TRUE,
               updated_at = NOW()
         WHERE account_code = %s
    """, (name, account_type, normal_balance, parent_account, code))
    cur.execute("""
        INSERT INTO accounting_accounts (
            account_code, account_name, account_type, normal_balance,
            account_level, parent_account, accepts_posting, active,
            created_by, updated_by
        )
        SELECT %s, %s, %s, %s, %s, %s, TRUE, TRUE, 'RULE_MIGRATION_2026', 'RULE_MIGRATION_2026'
        WHERE NOT EXISTS (
            SELECT 1 FROM accounting_accounts WHERE account_code = %s
        )
    """, (code, name, account_type, normal_balance, 4, parent_account, code))


def upsert_entry(cur, origin: str, origin_id: int, entry_date, period: str, description: str) -> int:
    cur.execute("""
        SELECT id
        FROM accounting_entries
        WHERE origin = %s
          AND origin_id = %s
        LIMIT 1
    """, (origin, origin_id))
    row = cur.fetchone()
    if row:
        entry_id = row["id"]
        cur.execute("""
            UPDATE accounting_entries
               SET entry_date = %s,
                   period = %s,
                   description = %s,
                   company_code = COALESCE(company_code, %s)
             WHERE id = %s
        """, (entry_date, period, description, COMPANY_CODE, entry_id))
        return entry_id

    cur.execute("""
        INSERT INTO accounting_entries (
            entry_date, period, description, origin, origin_id, created_by, company_code
        )
        VALUES (%s, %s, %s, %s, %s, 'RULE_MIGRATION_2026', %s)
        RETURNING id
    """, (entry_date, period, description, origin, origin_id, COMPANY_CODE))
    return cur.fetchone()["id"]


def insert_line(cur, entry_id: int, code: str, name: str, debit, credit, description: str):
    cur.execute("""
        INSERT INTO accounting_lines (
            entry_id, account_code, account_name, debit, credit, line_description
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (entry_id, code, name, money(debit), money(credit), description))


def snapshot_entries(cur, origin: str, origin_ids: list[int]):
    if not origin_ids:
        return []
    cur.execute("""
        SELECT e.id, e.origin, e.origin_id, e.entry_date, e.period, e.description,
               l.account_code, l.account_name, l.debit, l.credit, l.line_description
        FROM accounting_entries e
        LEFT JOIN accounting_lines l ON l.entry_id = e.id
        WHERE e.origin = %s
          AND e.origin_id = ANY(%s)
        ORDER BY e.origin_id, e.id, l.id
    """, (origin, origin_ids))
    return cur.fetchall() or []


def rebalance_bcr_cash_app_2026(cur, apply: bool):
    ensure_account(cur, "5.2.03", "Comisiones bancarias", "EXPENSE", "DEBIT", "5.2")

    cur.execute("""
        SELECT id, numero_documento, codigo_cliente, nombre_cliente, banco,
               monto_pagado, comision, fecha_pago, bank_account_code, bank_account_name
        FROM cash_app
        WHERE tipo_aplicacion = 'PAGO'
          AND fecha_pago >= %s
          AND fecha_pago < %s
        ORDER BY id
    """, (date(YEAR, 1, 1), date(YEAR + 1, 1, 1)))
    rows = cur.fetchall() or []

    changes = []
    affected_ids = []
    for row in rows:
        client_name = str(row.get("nombre_cliente") or "").strip()
        raw_bank = str(row.get("banco") or "").strip()
        account = resolve_collections_bank(
            cur,
            row.get("bank_account_code"),
            row.get("bank_account_name"),
            client_name,
            raw_bank,
        )
        bank_code = (account or {}).get("account_code") or row.get("bank_account_code") or "1.1.01"
        bank_name = (account or {}).get("account_name") or row.get("bank_account_name") or "Bancos"
        total_applied = money(row.get("monto_pagado")) + abs(money(row.get("comision")))
        applies = should_apply_bcr_collection_fee(
            cur,
            bank_code,
            bank_name,
            raw_bank,
            row.get("numero_documento"),
            row.get("codigo_cliente"),
            client_name,
        )
        new_fee = money(BCR_COLLECTION_FEE_USD) if applies and total_applied > money(BCR_COLLECTION_FEE_USD) else Decimal("0.00")
        new_paid = total_applied - new_fee
        old_paid = money(row.get("monto_pagado"))
        old_fee = abs(money(row.get("comision")))

        needs_update = old_paid != new_paid or old_fee != new_fee or bank_code != row.get("bank_account_code") or bank_name != row.get("bank_account_name")
        if not needs_update:
            continue

        affected_ids.append(int(row["id"]))
        changes.append({
            "cash_app_id": row["id"],
            "numero_documento": row.get("numero_documento"),
            "codigo_cliente": row.get("codigo_cliente"),
            "nombre_cliente": client_name,
            "applies_bcr_fee": applies,
            "old_monto_pagado": str(old_paid),
            "old_comision": str(old_fee),
            "new_monto_pagado": str(new_paid),
            "new_comision": str(new_fee),
            "bank_account_code": bank_code,
            "bank_account_name": bank_name,
        })

        if not apply:
            continue

        cur.execute("""
            UPDATE cash_app
               SET monto_pagado = %s,
                   comision = %s,
                   bank_account_code = %s,
                   bank_account_name = %s
             WHERE id = %s
        """, (new_paid, new_fee, bank_code, bank_name, row["id"]))

        fecha = to_date(row["fecha_pago"])
        tc = exchange_rate_for(cur, fecha)
        detail = f"Pago factura {row.get('numero_documento') or ''}".strip()
        entry_id = upsert_entry(cur, "CASH_APP", int(row["id"]), fecha, period_for(fecha), detail)
        cur.execute("DELETE FROM accounting_lines WHERE entry_id = %s", (entry_id,))
        if new_paid > 0:
            insert_line(cur, entry_id, bank_code, bank_name, new_paid * tc, 0, detail)
        if new_fee > 0:
            insert_line(cur, entry_id, "5.2.03", "Comisiones bancarias", new_fee * tc, 0, f"Comision - {detail}")
        insert_line(cur, entry_id, "1.1.04.01", "Cuentas por cobrar comerciales", 0, total_applied * tc, detail)

    return changes, affected_ids


def rebalance_surveyor_itp_payments_2026(cur, apply: bool):
    ensure_account(cur, "2.1.02.04", "Impuesto de renta por pagar", "LIABILITY", "CREDIT", "2.1.02")
    ensure_account(cur, "2.1.02.09", "Deducciones a surveyors del exterior por pagar", "LIABILITY", "CREDIT", "2.1.02")

    cur.execute("""
        SELECT id, payee_name, payee_type, obligation_type, reference, country,
               last_payment_date, currency, total, balance, status,
               payment_bank_account_code, payment_bank_account_name
        FROM payment_obligations
        WHERE active = TRUE
          AND status = 'PAID'
          AND COALESCE(balance, 0) = 0
          AND last_payment_date >= %s
          AND last_payment_date < %s
          AND (payee_type = 'SURVEYOR' OR obligation_type = 'SURVEYOR_FEE')
        ORDER BY id
    """, (date(YEAR, 1, 1), date(YEAR + 1, 1, 1)))
    rows = cur.fetchall() or []

    tc = latest_exchange_rate(cur)
    changes = []
    affected_ids = []
    for row in rows:
        total_raw = money(row.get("total"))
        if total_raw <= 0:
            continue

        settlement = external_surveyor_settlement(
            cur,
            total_raw,
            payee_name=row.get("payee_name"),
            fallback_country=row.get("country"),
            payee_type=row.get("payee_type"),
            obligation_type=row.get("obligation_type"),
        )

        currency = str(row.get("currency") or "").upper()
        calc_total = total_raw * tc if currency == "USD" else total_raw
        if settlement["applies"]:
            if currency == "USD":
                withholding_crc = money(settlement["withholding"] * tc)
                deduction_crc = money(settlement["deduction"] * tc)
            else:
                withholding_crc = money(calc_total * Decimal("0.25"))
                deduction_crc = min(money(Decimal("25.00") * tc), max(calc_total - withholding_crc, Decimal("0.00")))
            bank_crc = max(money(calc_total - withholding_crc - deduction_crc), Decimal("0.00"))
        else:
            withholding_crc = Decimal("0.00")
            deduction_crc = Decimal("0.00")
            bank_crc = calc_total

        affected_ids.append(int(row["id"]))
        changes.append({
            "obligation_id": row["id"],
            "payee_name": row.get("payee_name"),
            "country": row.get("country"),
            "currency": currency,
            "gross": str(total_raw),
            "external_rule_applies": bool(settlement["applies"]),
            "deduction_usd": str(settlement["deduction"]),
            "withholding_usd": str(settlement["withholding"]),
            "net_payment_usd": str(settlement["net_payment"]),
            "ap_crc": str(calc_total),
            "withholding_crc": str(withholding_crc),
            "deduction_crc": str(deduction_crc),
            "bank_crc": str(bank_crc),
        })

        if not apply:
            continue

        current_payee_name = str(row.get("payee_name") or "").strip()
        account = resolve_itp_bank(
            cur,
            row.get("payment_bank_account_code"),
            row.get("payment_bank_account_name"),
            payee_name=current_payee_name,
            payee_type=row.get("payee_type"),
            obligation_type=row.get("obligation_type"),
            country=row.get("country"),
            reference=row.get("reference"),
        )
        bank_code = (account or {}).get("account_code") or row.get("payment_bank_account_code") or "1.1.02"
        bank_name = (account or {}).get("account_name") or row.get("payment_bank_account_name") or "Bancos"
        if not account_exists(cur, bank_code):
            raise RuntimeError(f"Cuenta bancaria no existe en accounting_ledger: {bank_code}")

        payment_date = to_date(row["last_payment_date"])
        payment_detail = f"From ITP Payment done to {current_payee_name}"
        entry_id = upsert_entry(cur, "ITP_PAYMENT", int(row["id"]), payment_date, period_for(payment_date), payment_detail)
        cur.execute("DELETE FROM accounting_lines WHERE entry_id = %s", (entry_id,))
        insert_line(cur, entry_id, "2.1.01.01", "Cuentas por pagar-comerciales", calc_total, 0, payment_detail)
        if withholding_crc > 0:
            insert_line(cur, entry_id, "2.1.02.04", "Impuesto de renta por pagar", 0, withholding_crc, f"Retencion 25% - {payment_detail}")
        if deduction_crc > 0:
            insert_line(cur, entry_id, "2.1.02.09", "Deducciones a surveyors del exterior por pagar", 0, deduction_crc, f"Deduccion transferencia exterior - {payment_detail}")
        insert_line(cur, entry_id, bank_code, bank_name, 0, bank_crc, payment_detail)

    return changes, affected_ids


def main():
    parser = argparse.ArgumentParser(description="Reaplica reglas BCR y surveyors exterior sobre pagos 2026.")
    parser.add_argument("--apply", action="store_true", help="Aplica cambios. Sin esto solo genera preview y rollback.")
    args = parser.parse_args()

    conn = database.connect()
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        ensure_accounting_schemas(cur)

        bcr_changes, bcr_ids = rebalance_bcr_cash_app_2026(cur, args.apply)
        surveyor_changes, surveyor_ids = rebalance_surveyor_itp_payments_2026(cur, args.apply)

        before = {
            "cash_app_entries": rows_to_json(snapshot_entries(cur, "CASH_APP", bcr_ids)),
            "itp_payment_entries": rows_to_json(snapshot_entries(cur, "ITP_PAYMENT", surveyor_ids)),
        }

        report = {
            "year": YEAR,
            "applied": args.apply,
            "bcr_cash_app_changes": bcr_changes,
            "surveyor_payment_changes": surveyor_changes,
            "affected": {
                "cash_app": len(bcr_changes),
                "surveyor_payments": len(surveyor_changes),
            },
            "entry_snapshot": before,
        }

        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        suffix = "apply" if args.apply else "preview"
        report_path = REPORT_DIR / f"reapply_2026_payment_rules_{suffix}.json"
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

        if args.apply:
            conn.commit()
        else:
            conn.rollback()

        print(json.dumps({
            "applied": args.apply,
            "cash_app_changes": len(bcr_changes),
            "surveyor_payment_changes": len(surveyor_changes),
            "report": str(report_path),
        }, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
