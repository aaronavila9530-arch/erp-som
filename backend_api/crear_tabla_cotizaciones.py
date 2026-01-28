import psycopg2
from psycopg2 import sql

# ============================================================
# CONFIGURACIÓN CONEXIÓN (RAILWAY)
# ============================================================

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # ============================================================
    # SCHEMA COMERCIAL
    # ============================================================

    print("📁 Creando schema comercial (si no existe)...")
    cur.execute("""
        CREATE SCHEMA IF NOT EXISTS comercial;
    """)

    # ============================================================
    # TABLA COTIZACIONES
    # ============================================================

    print("🧱 Creando tabla comercial.cotizaciones...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS comercial.cotizaciones (

            -- ===============================
            -- IDENTIDAD
            -- ===============================
            id                  SERIAL PRIMARY KEY,
            codigo_cotizacion   VARCHAR(20) UNIQUE NOT NULL,

            -- ===============================
            -- REFERENCIAS COMERCIALES
            -- ===============================
            cliente             VARCHAR(100) NOT NULL,
            servicio            VARCHAR(100) NOT NULL,
            continente          VARCHAR(50),
            pais                VARCHAR(50),
            puerto              VARCHAR(100),

            -- ===============================
            -- CONDICIONES ECONÓMICAS
            -- ===============================
            precio              NUMERIC(12,2) NOT NULL,
            moneda              VARCHAR(10) DEFAULT 'USD',

            -- ===============================
            -- CONDICIONES OPERATIVAS
            -- ===============================
            fecha_servicio      DATE,
            validez_dias        INTEGER DEFAULT 15,
            terminos_pago       VARCHAR(100) DEFAULT '15 días',

            -- ===============================
            -- DOCUMENTO
            -- ===============================
            idioma              VARCHAR(5) NOT NULL
                CHECK (idioma IN ('ES', 'EN')),
            texto_cotizacion    TEXT NOT NULL,

            -- ===============================
            -- ESTADO COMERCIAL
            -- ===============================
            estado              VARCHAR(20) DEFAULT 'DRAFT'
                CHECK (estado IN ('DRAFT', 'ENVIADA', 'ACEPTADA', 'VENCIDA')),

            -- ===============================
            -- AUDITORÍA
            -- ===============================
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    # ============================================================
    # ÍNDICES
    # ============================================================

    print("⚡ Creando índices...")
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_cliente
        ON comercial.cotizaciones (cliente);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_servicio
        ON comercial.cotizaciones (servicio);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_estado
        ON comercial.cotizaciones (estado);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_cotizaciones_created_at
        ON comercial.cotizaciones (created_at);
    """)

    # ============================================================
    # FUNCIÓN CÓDIGO COTIZACIÓN
    # ============================================================

    print("🧠 Creando función generadora de código...")
    cur.execute("""
        CREATE OR REPLACE FUNCTION comercial.generate_codigo_cotizacion()
        RETURNS TEXT AS $$
        DECLARE
            yr TEXT := EXTRACT(YEAR FROM NOW())::TEXT;
            seq INT;
        BEGIN
            SELECT COUNT(*) + 1
            INTO seq
            FROM comercial.cotizaciones
            WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());

            RETURN 'COT-' || yr || '-' || LPAD(seq::TEXT, 4, '0');
        END;
        $$ LANGUAGE plpgsql;
    """)

    # ============================================================
    # TRIGGER
    # ============================================================

    print("🔁 Creando trigger automático...")
    cur.execute("""
        CREATE OR REPLACE FUNCTION comercial.before_insert_cotizacion()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.codigo_cotizacion IS NULL THEN
                NEW.codigo_cotizacion := comercial.generate_codigo_cotizacion();
            END IF;

            NEW.created_at := NOW();
            NEW.updated_at := NOW();

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    cur.execute("""
        DROP TRIGGER IF EXISTS trg_before_insert_cotizacion
        ON comercial.cotizaciones;
    """)

    cur.execute("""
        CREATE TRIGGER trg_before_insert_cotizacion
        BEFORE INSERT ON comercial.cotizaciones
        FOR EACH ROW
        EXECUTE FUNCTION comercial.before_insert_cotizacion();
    """)

    # ============================================================
    # FINAL
    # ============================================================

    cur.close()
    conn.close()

    print("✅ Tabla comercial.cotizaciones creada correctamente")
    print("🚀 Script ejecutado con éxito")


if __name__ == "__main__":
    main()
