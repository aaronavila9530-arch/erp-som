import psycopg2


DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    try:
        print("🔌 Conectando a la base de datos...")

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        print("🛠 Agregando columna 'customer'...")

        cur.execute("""
            ALTER TABLE vessel_truck_supervision_reports
            ADD COLUMN IF NOT EXISTS customer TEXT;
        """)

        print("✅ Columna 'customer' creada correctamente.")

        cur.close()
        conn.close()

        print("🎯 Proceso finalizado con éxito.")

    except Exception as e:
        print("❌ Error:")
        print(str(e))


if __name__ == "__main__":
    main()
