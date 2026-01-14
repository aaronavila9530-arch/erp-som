import psycopg2
from psycopg2 import sql

# ============================================================
# CONFIGURACIÓN DB (RAILWAY)
# ============================================================

DATABASE_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

# ============================================================
# SCRIPT DE ALTER TABLE
# ============================================================

def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        # ----------------------------------------------------
        # payroll_runs → nuevas columnas
        # ----------------------------------------------------
        print("🛠️ Alterando tabla payroll_runs...")

        cur.execute("""
            ALTER TABLE payroll_runs
            ADD COLUMN IF NOT EXISTS horas_extra NUMERIC(10,2),
            ADD COLUMN IF NOT EXISTS salario_bruto NUMERIC(14,2),
            ADD COLUMN IF NOT EXISTS monto_horas_extra NUMERIC(14,2);
        """)

        # ----------------------------------------------------
        # empleados → nueva columna
        # ----------------------------------------------------
        print("🛠️ Alterando tabla empleados...")

        cur.execute("""
            ALTER TABLE empleados
            ADD COLUMN IF NOT EXISTS cedula_id VARCHAR(50);
        """)

        conn.commit()
        print("✅ Cambios aplicados correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante la ejecución:")
        print(e)

    finally:
        cur.close()
        conn.close()
        print("🔒 Conexión cerrada.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
