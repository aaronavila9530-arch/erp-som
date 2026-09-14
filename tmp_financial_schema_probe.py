from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend_api"))

import database  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402


TABLES = ["collections", "invoice_to_pay", "invoice_to_pay_items", "itp_biweekly_payment_lines", "itp_biweekly_payment_batches", "invoicing", "payroll_runs", "empleados", "servicios"]


def main() -> None:
    conn = database.get_conn()
    out = {}
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            for table in TABLES:
                cur.execute(
                    """
                    SELECT column_name, data_type
                    FROM information_schema.columns
                    WHERE table_schema='public' AND table_name=%s
                    ORDER BY ordinal_position
                    """,
                    (table,),
                )
                columns = cur.fetchall()
                if not columns:
                    out[table] = {"columns": [], "sample": [], "missing": True}
                    continue
                cur.execute(f"SELECT * FROM {table} LIMIT 3")
                rows = cur.fetchall()
                out[table] = {"columns": columns, "sample": rows}
        print(json.dumps(out, default=str, indent=2, ensure_ascii=False))
    finally:
        database.release_conn(conn)


if __name__ == "__main__":
    main()
