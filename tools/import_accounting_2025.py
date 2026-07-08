from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend_api"
sys.path.insert(0, str(BACKEND))

import database  # noqa: E402


SOURCE_FILE = Path(r"C:\Users\aaron\Desktop\Expendiente Contable 2025.xlsx")
IMPORT_ORIGIN = "EXCEL_2025_EXPEDIENTE_CONTABLE"
SHEETS = ("Diario General", "Asientos Ajuste")


def dec(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value).strip())
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Valor numerico invalido: {value!r}") from exc


def parse_date(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    return date.fromisoformat(text[:10])


def load_entries():
    wb = openpyxl.load_workbook(SOURCE_FILE, data_only=True, read_only=True)
    entries: dict[tuple[str, str], dict] = {}

    for sheet_name in SHEETS:
        ws = wb[sheet_name]
        for row in ws.iter_rows(min_row=4, values_only=True):
            if not row or not row[0] or not row[1]:
                continue
            entry_date = parse_date(row[0])
            asiento = str(row[1]).strip()
            concept = str(row[2] or "").strip()
            account_code = str(row[3] or "").strip()
            account_name = str(row[4] or "").strip()
            debit = dec(row[5])
            credit = dec(row[6])
            if not account_code or (debit == 0 and credit == 0):
                continue

            key = (sheet_name, asiento)
            entry = entries.setdefault(
                key,
                {
                    "entry_date": entry_date,
                    "period": entry_date.strftime("%Y-%m"),
                    "description": f"{asiento} - {concept}",
                    "source_key": f"{sheet_name}:{asiento}",
                    "lines": [],
                },
            )
            entry["lines"].append(
                {
                    "account_code": account_code,
                    "account_name": account_name,
                    "debit": debit,
                    "credit": credit,
                    "line_description": concept,
                }
            )

    return list(entries.values())


def verify_entries(entries):
    bad = []
    totals = defaultdict(Decimal)
    line_count = 0
    for entry in entries:
        debit = sum(line["debit"] for line in entry["lines"])
        credit = sum(line["credit"] for line in entry["lines"])
        line_count += len(entry["lines"])
        totals["debit"] += debit
        totals["credit"] += credit
        if debit.quantize(Decimal("0.01")) != credit.quantize(Decimal("0.01")):
            bad.append((entry["source_key"], debit, credit))
    if bad:
        for item in bad[:20]:
            print("UNBALANCED", item)
        raise SystemExit(f"Asientos sin balance: {len(bad)}")
    return line_count, totals["debit"], totals["credit"]


def ensure_ledger_accounts(cur, entries):
    accounts = {}
    for entry in entries:
        for line in entry["lines"]:
            accounts.setdefault(line["account_code"], line["account_name"])

    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'accounting_ledger'
        """
    )
    columns = {row[0] for row in cur.fetchall()}

    inserted = 0
    for code, name in accounts.items():
        cur.execute("SELECT 1 FROM accounting_ledger WHERE account_code = %s LIMIT 1", (code,))
        if cur.fetchone():
            continue
        if {"account_code", "account_name", "account_type", "account_level", "parent_account"}.issubset(columns):
            cur.execute(
                """
                INSERT INTO accounting_ledger
                (account_code, account_name, account_type, account_level, parent_account)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (code, name, "IMPORT_2025", 0, None),
            )
        else:
            cur.execute(
                """
                INSERT INTO accounting_ledger (account_code, account_name)
                VALUES (%s, %s)
                """,
                (code, name),
            )
        inserted += 1
    return inserted


def import_entries(entries, dry_run=False):
    conn = database.connect()
    try:
        cur = conn.cursor()

        cur.execute(
            """
            SELECT COUNT(1)
            FROM accounting_entries
            WHERE origin = %s
            """,
            (IMPORT_ORIGIN,),
        )
        existing = int(cur.fetchone()[0] or 0)

        cur.execute(
            """
            SELECT COUNT(1)
            FROM accounting_entries
            WHERE period LIKE '2025-%'
            """,
        )
        existing_2025 = int(cur.fetchone()[0] or 0)

        line_count, total_debit, total_credit = verify_entries(entries)
        print(f"PREVIEW entries={len(entries)} lines={line_count} debit={total_debit:.2f} credit={total_credit:.2f}")
        print(f"EXISTING origin={existing} all_2025_entries={existing_2025}")

        if dry_run:
            conn.rollback()
            return

        if existing:
            cur.execute(
                """
                DELETE FROM accounting_entries
                WHERE origin = %s
                """,
                (IMPORT_ORIGIN,),
            )

        ledger_inserted = ensure_ledger_accounts(cur, entries)

        for import_index, entry in enumerate(entries, start=1):
            cur.execute(
                """
                INSERT INTO accounting_entries
                (entry_date, period, description, origin, origin_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    entry["entry_date"],
                    entry["period"],
                    entry["description"],
                    IMPORT_ORIGIN,
                    import_index,
                ),
            )
            entry_id = cur.fetchone()[0]
            for line in entry["lines"]:
                cur.execute(
                    """
                    INSERT INTO accounting_lines
                    (entry_id, account_code, account_name, debit, credit, line_description)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry_id,
                        line["account_code"],
                        line["account_name"],
                        line["debit"],
                        line["credit"],
                        line["line_description"],
                    ),
                )

        conn.commit()
        print(f"IMPORTED entries={len(entries)} lines={line_count} ledger_accounts_added={ledger_inserted}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    import_entries(load_entries(), dry_run=dry_run)
