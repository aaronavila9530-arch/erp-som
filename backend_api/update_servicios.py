import psycopg2

# =========================================================
# CONEXIÓN
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def main():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print("✅ Conectado a la base de datos")

        # =====================================================
        # UPDATES
        # =====================================================
        updates = [
            (428, "2166-0604-2026"),
            (433, "2165-0604-2026"),
            (434, "2167-0604-2026"),
        ]

        for consec, num_informe in updates:
            cur.execute("""
                UPDATE servicios
                SET num_informe = %s
                WHERE consec = %s
            """, (num_informe, consec))

            print(f"🔄 consec {consec} → num_informe = {num_informe}")

        conn.commit()
        print("✅ Cambios guardados correctamente")

    except Exception as e:
        print("❌ ERROR:", str(e))
        if 'conn' in locals():
            conn.rollback()

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()