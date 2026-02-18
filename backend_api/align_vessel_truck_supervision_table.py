import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


def main():

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("🔧 Alineando tabla vessel_truck_supervision_reports...")

    # =========================================================
    # 1️⃣ AGREGAR NUEVAS COLUMNAS SI NO EXISTEN
    # =========================================================

    alter_queries = [
        """
        ALTER TABLE vessel_truck_supervision_reports
        ADD COLUMN IF NOT EXISTS findings_documental_text TEXT;
        """,
        """
        ALTER TABLE vessel_truck_supervision_reports
        ADD COLUMN IF NOT EXISTS findings_operational_text TEXT;
        """,
        """
        ALTER TABLE vessel_truck_supervision_reports
        ADD COLUMN IF NOT EXISTS incidents_text TEXT;
        """
    ]

    for q in alter_queries:
        cur.execute(q)

    print("✅ Nuevas columnas agregadas (si no existían).")

    # =========================================================
    # 2️⃣ MIGRAR DATOS EXISTENTES
    # =========================================================

    cur.execute("""
        UPDATE vessel_truck_supervision_reports
        SET findings_documental_text = findings_text
        WHERE findings_text IS NOT NULL
          AND findings_documental_text IS NULL;
    """)

    print("✅ Datos migrados desde findings_text.")

    # =========================================================
    # 3️⃣ ELIMINAR COLUMNA ANTIGUA (OPCIONAL)
    # =========================================================
    # Si quieres conservarla, comenta esta parte

    cur.execute("""
        ALTER TABLE vessel_truck_supervision_reports
        DROP COLUMN IF EXISTS findings_text;
    """)

    print("✅ Columna findings_text eliminada.")

    cur.close()
    conn.close()

    print("🎯 Tabla alineada correctamente 1:1 con el form.")


if __name__ == "__main__":
    main()
