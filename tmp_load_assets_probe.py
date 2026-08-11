from backend_api.database import connect
from datetime import date
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend_api"))


def main():
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND (
                table_name ILIKE '%asset%'
                OR table_name ILIKE '%activo%'
                OR table_name ILIKE '%depreci%'
              )
            ORDER BY table_name
            """
        )
        print("tables:", cur.fetchall())
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name ILIKE '%exchange%'
            ORDER BY table_name
            """
        )
        print("exchange tables:", cur.fetchall())
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'exchange_rate'
            ORDER BY ordinal_position
            """
        )
        print("exchange columns:", cur.fetchall())
        cur.execute(
            """
            SELECT *
            FROM exchange_rate
            WHERE rate_date <= DATE '2024-12-31'
            ORDER BY rate_date DESC
            LIMIT 5
            """
        )
        print("exchange sample 2024:", cur.fetchall())

        try:
            from backend_api.routers.exchange_rate import _fetch_tc_venta_from_bccr
            rate, rate_date = _fetch_tc_venta_from_bccr(date(2024, 12, 31))
            print("bccr 2024-12-31:", rate, rate_date)
        except Exception as exc:
            print("bccr error:", repr(exc))
        cur.execute(
            """
            SELECT account_code, account_name, account_type, active
            FROM accounting_accounts
            WHERE account_type = 'ASSET'
               OR account_name ILIKE '%mueble%'
               OR account_name ILIKE '%equipo%'
               OR account_name ILIKE '%depreci%'
            ORDER BY account_code
            """
        )
        print("asset accounts:")
        for row in cur.fetchall():
            print(row)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
