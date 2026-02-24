import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLES = [
    "draft_survey_word_report",
    "draft_survey_ballast",
    "draft_survey",
    "general_draft_survey"
]

def main():
    conn = None
    cur = None

    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("⚠️  Vaciando tablas y reiniciando IDs...")

        for table in TABLES:
            print(f"   → TRUNCATE {table}")
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

        conn.commit()

        print("\n✅ Tablas limpiadas correctamente.")
        print("🔁 IDs reiniciados desde 1.")
        print("🚀 Sistema listo para empezar limpio.")

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