import psycopg2

# =========================================================
# 🔗 CONEXIÓN
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def reset_tables():
    conn = None
    cur = None

    try:
        print("🔌 Conectando a DB...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # =====================================================
        # ⚠️ ORDEN IMPORTANTE POR FOREIGN KEYS
        # =====================================================
        tables = [
            "draft_survey_word_report",
            "draft_survey_ballast",
            "draft_survey",
            "general_draft_survey"
        ]

        print("🧹 Limpiando tablas...")

        for table in tables:
            print(f"   → DELETE FROM {table}")
            cur.execute(f"DELETE FROM {table};")

        print("🔄 Reseteando sequences...")

        # =====================================================
        # RESET DE IDS (SERIAL / IDENTITY)
        # =====================================================
        for table in tables:
            print(f"   → RESET ID {table}")

            cur.execute(f"""
                SELECT pg_get_serial_sequence('{table}', 'id');
            """)
            seq = cur.fetchone()[0]

            if seq:
                cur.execute(f"ALTER SEQUENCE {seq} RESTART WITH 1;")
            else:
                print(f"   ⚠️ No sequence encontrada para {table}")

        conn.commit()
        print("✅ Todo limpio y reseteado correctamente.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:", str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    reset_tables()