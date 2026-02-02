import psycopg2
from psycopg2 import sql


DB_URL = (
    "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)


def main():
    conn = None
    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # =====================================================
        # 1. DROP TABLES (SI EXISTEN)
        # =====================================================
        print("🧨 Eliminando tablas comerciales...")

        cur.execute("""
            DROP TABLE IF EXISTS commercial_operations_fact CASCADE;
        """)
        print("   ✔ commercial_operations_fact eliminada")

        cur.execute("""
            DROP TABLE IF EXISTS commercial_pricing_context CASCADE;
        """)
        print("   ✔ commercial_pricing_context eliminada")

        # =====================================================
        # 2. LIMPIAR TABLA COTIZACIONES + RESET ID
        # =====================================================
        print("🧹 Limpiando tabla cotizaciones y reseteando ID...")

        cur.execute("""
            TRUNCATE TABLE cotizaciones RESTART IDENTITY CASCADE;
        """)
        print("   ✔ cotizaciones vaciada y secuencia reseteada")

        # =====================================================
        # 3. LIMPIAR TABLAS HHRR Y NOTICIAS
        # =====================================================
        print("🧹 Limpiando tablas HHRR y noticias...")

        cur.execute("""
            TRUNCATE TABLE
                hr_events,
                hr_ot_log,
                noticias,
                payroll_runs
            RESTART IDENTITY CASCADE;
        """)
        print("   ✔ hr_events, hr_ot_log, noticias, payroll_runs limpiadas")

        # =====================================================
        # COMMIT
        # =====================================================
        conn.commit()
        print("✅ OPERACIÓN COMPLETADA CON ÉXITO")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR DURANTE LA OPERACIÓN")
        print(str(e))

    finally:
        if conn:
            conn.close()
            print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()
