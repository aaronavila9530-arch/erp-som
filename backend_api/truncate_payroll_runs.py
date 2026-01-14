import psycopg2

# ============================================================
# CONFIGURACIÓN DB (RAILWAY)
# ============================================================

DATABASE_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

# ============================================================
# SCRIPT
# ============================================================

def main():
    print("⚠️ ATENCIÓN: Este script eliminará TODOS los registros de payroll_runs")
    confirm = input("Escriba SI para continuar: ").strip().upper()

    if confirm != "SI":
        print("❌ Operación cancelada.")
        return

    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🧹 Blanqueando tabla payroll_runs...")

        cur.execute("TRUNCATE TABLE payroll_runs RESTART IDENTITY CASCADE;")

        conn.commit()
        print("✅ Tabla payroll_runs vaciada correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante el truncado:")
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
