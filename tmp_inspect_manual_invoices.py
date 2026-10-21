import pathlib
import re

import psycopg2


def dsn_from_existing_script() -> str:
    text = pathlib.Path("tmp_report_table_columns.py").read_text(encoding="utf-8")
    head = text.split("tables = [", 1)[0]
    parts = [
        part
        for part in re.findall(r'"([^"]*)"', head)
        if part.startswith(("postgresql://", "postgres://", "@", "railway", "?sslmode", "L"))
    ]
    return "".join(parts)


def main() -> None:
    conn = psycopg2.connect(dsn_from_existing_script())
    cur = conn.cursor()
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
          AND table_name IN ('invoicing','factura','factura_detalle','collections')
        ORDER BY table_name
        """
    )
    print("tables", cur.fetchall())
    cur.execute(
        """
        SELECT column_name,data_type
        FROM information_schema.columns
        WHERE table_schema='public'
          AND table_name='invoicing'
        ORDER BY ordinal_position
        """
    )
    print("invoicing_columns")
    for row in cur.fetchall():
        print(row)
    for table, where in [
        ("invoicing", "tipo_factura='MANUAL' AND tipo_documento='FACTURA'"),
        ("factura", "tipo_factura='MANUAL'"),
    ]:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}")
        print(table, cur.fetchone()[0])
    cur.execute(
        """
        SELECT id, company_code, factura_id, numero_documento, nombre_cliente,
               fecha_emision, moneda, total, pdf_path
        FROM invoicing
        WHERE tipo_factura='MANUAL'
          AND tipo_documento='FACTURA'
        ORDER BY id
        LIMIT 20
        """
    )
    print("sample")
    for row in cur.fetchall():
        print(row)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
