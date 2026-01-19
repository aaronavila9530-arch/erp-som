import psycopg2
import pandas as pd
import sys
import os

# ======================================================
# CONFIGURACIÓN
# ======================================================
DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"
EXCEL_FILE = "eliminar payments obligations.xlsx"
TABLE_NAME = "payment_obligations"


def main():
    print("=== DELETE PAYMENTS OBLIGATIONS FROM EXCEL ===\n")

    if not os.path.exists(EXCEL_FILE):
        print(f"❌ No se encontró el archivo: {EXCEL_FILE}")
        sys.exit(1)

    try:
        df = pd.read_excel(EXCEL_FILE)
    except Exception as e:
        print("❌ Error leyendo el Excel")
        print(e)
        sys.exit(1)

    if "id" not in df.columns:
        print("❌ El Excel NO contiene la columna 'id'")
        print("Columnas encontradas:", list(df.columns))
        sys.exit(1)

    ids = df["id"].dropna().astype(int).tolist()

    if not ids:
        print("⚠️ No hay IDs para eliminar")
        sys.exit(0)

    print(f"🔎 IDs a eliminar: {len(ids)}")
    print(ids)

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        cur.execute(
            f"""
            DELETE FROM {TABLE_NAME}
            WHERE id = ANY(%s)
            """,
            (ids,)
        )

        deleted = cur.rowcount
        conn.commit()

        print(f"\n✅ Eliminadas {deleted} filas de '{TABLE_NAME}'")

        cur.close()
        conn.close()

    except Exception as e:
        print("\n❌ ERROR durante eliminación")
        print(e)
        try:
            conn.rollback()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
