# ============================================================
# CREAR TABLA — SERVICIOS PRECIOS (ERP-SOM)
# Ejecutar desde CMD
# ============================================================

import psycopg2
from psycopg2 import sql


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    conn = None
    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True

        cur = conn.cursor()

        print("🧱 Creando tabla servicios_precios...")

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS servicios_precios (
            id SERIAL PRIMARY KEY,

            servicio   TEXT NOT NULL,
            cliente    TEXT NOT NULL,

            continente TEXT,
            pais       TEXT,
            puerto     TEXT,

            precio     NUMERIC(12,2) NOT NULL,

            activo     BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
        """

        cur.execute(create_table_sql)

        print("✅ Tabla servicios_precios creada correctamente.")

        # Índices útiles (performance futura)
        print("⚙️ Creando índices...")

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_servicios_precios_servicio
            ON servicios_precios (servicio);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_servicios_precios_cliente
            ON servicios_precios (cliente);
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_servicios_precios_geo
            ON servicios_precios (continente, pais, puerto);
        """)

        print("✅ Índices creados.")

        cur.close()

    except Exception as e:
        print("❌ Error:", e)

    finally:
        if conn:
            conn.close()
            print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
