import psycopg2
from psycopg2 import sql

# ============================================================
# CONFIG
# ============================================================

DATABASE_URL = (
    "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

# ============================================================
# MAIN
# ============================================================

def main():
    conn = None

    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # ====================================================
        # 1. DROP SCHEMA COMERCIAL
        # ====================================================
        print("🧹 Eliminando schema 'comercial' (si existe)...")
        cur.execute("""
            DROP SCHEMA IF EXISTS comercial CASCADE;
        """)

        # ====================================================
        # 2. CREATE TABLE IN PUBLIC
        # ====================================================
        print("🏗️ Creando tabla public.cotizaciones...")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS public.cotizaciones (
                id SERIAL PRIMARY KEY,

                cliente VARCHAR(255) NOT NULL,
                servicio VARCHAR(255),
                continente VARCHAR(100),
                pais VARCHAR(100),
                puerto VARCHAR(100),

                precio NUMERIC(14,2),

                idioma VARCHAR(5) DEFAULT 'ES',
                validez INTEGER,

                status VARCHAR(50) DEFAULT 'ACTIVA',

                servicio_1 VARCHAR(255),
                precio_1 NUMERIC(14,2),

                servicio_2 VARCHAR(255),
                precio_2 NUMERIC(14,2),

                servicio_3 VARCHAR(255),
                precio_3 NUMERIC(14,2),

                servicio_4 VARCHAR(255),
                precio_4 NUMERIC(14,2),

                quotation_number VARCHAR(20) UNIQUE NOT NULL,

                razon_cancelacion TEXT,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        print("✅ Proceso finalizado correctamente.")

    except Exception as e:
        print("❌ ERROR:")
        print(str(e))

    finally:
        if conn:
            conn.close()
            print("🔒 Conexión cerrada.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
