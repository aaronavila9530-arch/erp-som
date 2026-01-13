import psycopg2
from psycopg2 import sql

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print("📄 Creando tabla payroll_runs (si no existe)...")

        cur.execute("""
            CREATE TABLE IF NOT EXISTS payroll_runs (
                id SERIAL PRIMARY KEY,

                -- Identificación del empleado
                usuario VARCHAR(50) NOT NULL,

                -- Periodo de la planilla
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,

                -- Resultado financiero
                salario_neto NUMERIC(12,2) NOT NULL,

                -- Ruta del PDF generado
                pdf_path TEXT,

                -- Auditoría
                generado_por VARCHAR(50) NOT NULL,
                creado_en TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

                -- Restricción: una planilla por empleado por periodo
                CONSTRAINT uq_payroll_runs_period
                    UNIQUE (usuario, year, month)
            );
        """)

        conn.commit()

        print("✅ Tabla payroll_runs creada o ya existente.")

        # Verificación básica
        cur.execute("SELECT COUNT(*) FROM payroll_runs;")
        count = cur.fetchone()[0]
        print(f"📊 Registros actuales en payroll_runs: {count}")

        cur.close()
        conn.close()

        print("🚀 Proceso finalizado correctamente.")

    except Exception as e:
        print("❌ ERROR CRÍTICO")
        print(str(e))


if __name__ == "__main__":
    main()
