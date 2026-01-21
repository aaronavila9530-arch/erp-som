import psycopg2

DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("📦 Creando tablas del módulo Comercial...")

    # =========================================================
    # TABLA 1 — FACT OPERATIONS
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commercial_operations_fact (
            id SERIAL PRIMARY KEY,
            operation_code TEXT UNIQUE,
            cliente_codigo TEXT,
            cliente_nombre TEXT,
            pais TEXT,
            puerto TEXT,
            servicio TEXT,
            tipo_operacion TEXT,
            surveyor TEXT,
            estado TEXT,
            fecha_estimadainicio DATE,
            fecha_real_fin DATE,
            ingreso_estimado NUMERIC(14,2),
            ingreso_real NUMERIC(14,2),
            costo_estimado NUMERIC(14,2),
            costo_real NUMERIC(14,2),
            margen_bruto NUMERIC(14,2),
            margen_neto NUMERIC(14,2),
            moneda TEXT,
            dias_operacion INTEGER,
            rentable BOOLEAN,
            comentarios TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # =========================================================
    # TABLA 2 — PRICING CONTEXT
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS commercial_pricing_context (
            id SERIAL PRIMARY KEY,
            cliente_codigo TEXT,
            cliente_nombre TEXT,
            tipo_cliente TEXT,
            pais TEXT,
            puerto TEXT,
            servicio TEXT,
            precio_base NUMERIC(14,2),
            descuento_pct NUMERIC(5,2),
            precio_final NUMERIC(14,2),
            moneda TEXT,
            nivel_complejidad INTEGER,
            comentario_puerto TEXT,
            contrato_activo BOOLEAN,
            fecha_inicio DATE,
            fecha_fin DATE,
            activo BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tablas comerciales creadas correctamente.")

if __name__ == "__main__":
    main()
