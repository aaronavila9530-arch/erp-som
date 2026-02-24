import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def main():
    conn = None
    cur = None

    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("🔎 Eliminando foreign key constraint...")

        cur.execute("""
            ALTER TABLE draft_survey_word_report
            DROP CONSTRAINT IF EXISTS draft_survey_word_report_draft_survey_id_fkey;
        """)

        conn.commit()

        print("✅ Foreign key eliminada correctamente.")
        print("🚀 Ahora Word puede insertar sin depender de draft_survey.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:")
        print(str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()