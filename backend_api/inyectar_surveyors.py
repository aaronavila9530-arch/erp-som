import os
import psycopg2
import pandas as pd


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

BASE_DIR = r"C:\Users\Aaron Avila\Documents\ERP-SOM\backend_api"
EXCEL_FILE = os.path.join(BASE_DIR, "surveyors.xlsx")
TABLE_NAME = "surveyor"

# Columnas que NUNCA deben inyectarse desde Excel
EXCLUDED_COLUMNS = {
    "id",
    "creado_en",
    "pais_id"
}


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        print(f"📄 Leyendo archivo Excel: {EXCEL_FILE}")
        df = pd.read_excel(EXCEL_FILE)

        if df.empty:
            raise Exception("El archivo Excel está vacío.")

        # Normalizar columnas
        df.columns = [c.strip().lower() for c in df.columns]

        cur = conn.cursor()

        # Columnas reales en la tabla
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (TABLE_NAME,))
        table_columns = {row[0] for row in cur.fetchall()}

        # Columnas finales a insertar
        insert_columns = [
            c for c in df.columns
            if c in table_columns and c not in EXCLUDED_COLUMNS
        ]

        if not insert_columns:
            raise Exception("No hay columnas válidas para insertar.")

        print("📌 Columnas a insertar:")
        for c in insert_columns:
            print("   -", c)

        # Limpiar NaN → None
        df = df[insert_columns].where(pd.notna(df), None)

        placeholders = ", ".join(["%s"] * len(insert_columns))
        columns_sql = ", ".join(insert_columns)

        sql = f"""
            INSERT INTO {TABLE_NAME} ({columns_sql})
            VALUES ({placeholders})
        """

        print("📥 Insertando registros...")

        for _, row in df.iterrows():
            cur.execute(sql, tuple(row[c] for c in insert_columns))

        conn.commit()
        print(f"✅ Inserción completada. Filas insertadas: {len(df)}")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante la inyección:")
        print(e)

    finally:
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
