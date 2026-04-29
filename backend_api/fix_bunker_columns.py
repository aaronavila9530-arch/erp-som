import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE_NAME = "vessel_bunker_reports"


def main():
    print("🔌 Conectando a la base de datos...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        # -----------------------------------------------------
        # Obtener columnas gauge_mtrs
        # -----------------------------------------------------
        print("🔍 Buscando columnas *_gauge_mtrs...")

        cur.execute(f"""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name LIKE '%%_gauge_mtrs'
        """, (TABLE_NAME,))

        columns = cur.fetchall()

        if not columns:
            print("⚠️ No se encontraron columnas gauge_mtrs.")
            return

        print(f"📦 Encontradas {len(columns)} columnas")

        # -----------------------------------------------------
        # Alterar solo las que no son TEXT
        # -----------------------------------------------------
        for col_name, data_type in columns:

            print(f"➡️ {col_name} ({data_type})")

            if data_type == "text":
                print(f"   ✅ Ya es TEXT, se omite")
                continue

            sql = f"""
                ALTER TABLE {TABLE_NAME}
                ALTER COLUMN {col_name}
                TYPE TEXT
                USING {col_name}::TEXT
            """

            print(f"   🔧 Alterando a TEXT...")
            cur.execute(sql)

        conn.commit()

        print("✅ Conversión completada correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ Error:", str(e))

    finally:
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()