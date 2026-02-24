import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLES = [
    "draft_survey",
    "draft_survey_ballast",
    "draft_survey_word_report",
    "general_draft_survey"
]

COLUMNS = {
    "year": "INTEGER",
    "month": "INTEGER",
    "continent": "VARCHAR(100)",
    "country": "VARCHAR(150)",
    "port": "VARCHAR(150)",
    "client": "VARCHAR(200)",
    "draft_report_number": "VARCHAR(100)"
}


def column_exists(cur, table, column):
    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
        AND column_name = %s;
    """, (table, column))
    return cur.fetchone() is not None


def main():
    conn = None
    cur = None

    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        for table in TABLES:
            print(f"\n📌 Procesando tabla: {table}")

            for column, datatype in COLUMNS.items():

                if not column_exists(cur, table, column):
                    print(f"   ➕ Agregando columna: {column}")
                    cur.execute(
                        f"ALTER TABLE {table} ADD COLUMN {column} {datatype};"
                    )
                else:
                    print(f"   ⚠ Columna ya existe: {column}")

        conn.commit()
        print("\n✅ Columnas agregadas correctamente en todas las tablas.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("\n❌ ERROR:")
        print(str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()