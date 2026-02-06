import psycopg2

# =====================================================
# DATABASE CONNECTION (RAILWAY)
# =====================================================
DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

# =====================================================
# DDL — TABLA PROYECTOS_CALCULO
# =====================================================
DDL = """
CREATE TABLE IF NOT EXISTS proyectos_calculo (
    id SERIAL PRIMARY KEY,

    nombre_proyecto TEXT NOT NULL,

    personal NUMERIC DEFAULT 0,
    costo NUMERIC DEFAULT 0,
    moneda TEXT DEFAULT 'USD',
    tiempo NUMERIC DEFAULT 0,

    total_honorarios NUMERIC DEFAULT 0,

    gasto_alimentacion NUMERIC DEFAULT 0,
    gasto_comunicacion NUMERIC DEFAULT 0,
    gasto_transporte NUMERIC DEFAULT 0,
    total_gastos NUMERIC DEFAULT 0,

    margen NUMERIC DEFAULT 0,
    precio NUMERIC DEFAULT 0,
    utilidad NUMERIC DEFAULT 0,

    comentarios TEXT,

    creado_el TIMESTAMP DEFAULT NOW()
);
"""

# =====================================================
# MAIN
# =====================================================
def main():
    print("🔧 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🧱 Creando tabla proyectos_calculo...")
    cur.execute(DDL)
    conn.commit()

    cur.close()
    conn.close()

    print("✅ Tabla proyectos_calculo creada correctamente.")

# =====================================================
# ENTRYPOINT
# =====================================================
if __name__ == "__main__":
    main()
