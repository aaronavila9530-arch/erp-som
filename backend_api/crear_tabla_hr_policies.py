import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("🛠️ Creando tabla hr_policies (si no existe)...")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hr_policies (
            id SERIAL PRIMARY KEY,

            categoria VARCHAR(100) NOT NULL,
            titulo VARCHAR(200) NOT NULL,

            contenido TEXT NOT NULL,

            articulo_ref VARCHAR(50),

            activo BOOLEAN NOT NULL DEFAULT TRUE,

            creado_por VARCHAR(100) NOT NULL,
            creado_en TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            actualizado_en TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    print("📌 Creando índices...")

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_hr_policies_categoria
        ON hr_policies (categoria);
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_hr_policies_activo
        ON hr_policies (activo);
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla hr_policies creada correctamente.")


if __name__ == "__main__":
    main()
