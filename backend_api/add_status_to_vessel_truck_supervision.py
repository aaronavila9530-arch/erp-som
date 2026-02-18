import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


def main():

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("🔧 Agregando columna status...")

    # =========================================================
    # AGREGAR COLUMNA
    # =========================================================
    cur.execute("""
        ALTER TABLE vessel_truck_supervision_reports
        ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'draft';
    """)

    print("✅ Columna status creada correctamente.")

    cur.close()
    conn.close()

    print("🎯 Proceso finalizado sin errores.")


if __name__ == "__main__":
    main()
