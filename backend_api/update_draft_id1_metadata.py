import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLES = [
    "draft_survey",
    "draft_survey_ballast",
    "draft_survey_word_report",
    "general_draft_survey"
]

DATA = {
    "continent": "America",
    "country": "Costa Rica",
    "year": 2026,
    "month": 2,
    "client": "El Surco",
    "draft_report_number": "2151-0102-2026",
    "port": "Caldera"
}


def main():
    conn = None
    cur = None

    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        for table in TABLES:
            print(f"\n📌 Actualizando tabla: {table}")

            # Verificar si existe ID = 1
            cur.execute(f"SELECT id FROM {table} WHERE id = 1;")
            exists = cur.fetchone()

            if exists:
                cur.execute(f"""
                    UPDATE {table}
                    SET
                        continent = %(continent)s,
                        country = %(country)s,
                        year = %(year)s,
                        month = %(month)s,
                        client = %(client)s,
                        draft_report_number = %(draft_report_number)s,
                        port = %(port)s
                    WHERE id = 1;
                """, DATA)

                print("   ✅ ID 1 actualizado correctamente.")
            else:
                print("   ⚠ ID 1 no existe en esta tabla. No se actualizó.")

        conn.commit()
        print("\n🚀 Actualización completada en todas las tablas.")

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