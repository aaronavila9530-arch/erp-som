import psycopg2
import pandas as pd
import sys
import os
from datetime import datetime

# ======================================================
# CONFIGURACIÓN FIJA (LA QUE TÚ DISTE)
# ======================================================
DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

EXCEL_FILE = r"C:\Users\Aaron Avila\Documents\ERP-SOM\backend_api\ACTUALIZAR PAYMENTS.xlsx"

TABLE_NAME = "payment_obligations"


def find_table_schema(cursor, table_name: str) -> str | None:
    """
    Devuelve el schema REAL donde existe la tabla.
    Si no existe, retorna None.
    """
    cursor.execute(
        """
        SELECT n.nspname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = %s
          AND c.relkind = 'r'
        """,
        (table_name,)
    )
    row = cursor.fetchone()
    return row[0] if row else None


def main():
    print("=== UPDATE PAYMENT_OBLIGATIONS (REAL & BLINDADO) ===\n")

    # --------------------------------------------------
    # Validar Excel
    # --------------------------------------------------
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ No se encontró el archivo:\n{EXCEL_FILE}")
        sys.exit(1)

    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print("❌ Error leyendo el Excel")
        print(e)
        sys.exit(1)

    # Normalizar columnas
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"id", "last_payment_date", "balance", "status"}
    if not required.issubset(df.columns):
        print("❌ El Excel NO contiene las columnas requeridas")
        print("Requeridas:", required)
        print("Encontradas:", list(df.columns))
        sys.exit(1)

    df = df.dropna(subset=["id"])

    if df.empty:
        print("⚠️ No hay registros para actualizar")
        sys.exit(0)

    print(f"📄 Registros en Excel: {len(df)}")

    # --------------------------------------------------
    # Conexión DB
    # --------------------------------------------------
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # --------------------------------------------------
        # 🔍 Detectar schema REAL
        # --------------------------------------------------
        schema = find_table_schema(cur, TABLE_NAME)

        if not schema:
            print(f"❌ La tabla '{TABLE_NAME}' NO existe en esta base de datos")
            print("   Verifica nombre exacto en PostgreSQL.")
            sys.exit(1)

        print(f"✅ Tabla encontrada en schema: {schema}")

        sql = f"""
            UPDATE {schema}.{TABLE_NAME}
            SET
                last_payment_date = %s,
                balance = %s,
                status = %s
            WHERE id = %s
        """

        updated = 0

        for _, row in df.iterrows():
            # Fecha
            last_payment_date = row["last_payment_date"]
            if pd.isna(last_payment_date):
                last_payment_date = None
            elif isinstance(last_payment_date, pd.Timestamp):
                last_payment_date = last_payment_date.date()
            elif isinstance(last_payment_date, datetime):
                last_payment_date = last_payment_date.date()

            balance = float(row["balance"]) if not pd.isna(row["balance"]) else 0.0
            status = str(row["status"]).strip()

            cur.execute(
                sql,
                (
                    last_payment_date,
                    balance,
                    status,
                    int(row["id"])
                )
            )

            updated += cur.rowcount

        conn.commit()

        print(f"\n✅ Filas actualizadas correctamente: {updated}")

        cur.close()
        conn.close()

    except Exception as e:
        print("\n❌ ERROR durante actualización")
        print(e)
        try:
            conn.rollback()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
