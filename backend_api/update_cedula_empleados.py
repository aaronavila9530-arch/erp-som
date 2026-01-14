import psycopg2

# ============================================================
# CONFIGURACIÓN DB (RAILWAY)
# ============================================================

DATABASE_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

# ============================================================
# DATA A INYECTAR: codigo -> cedula_id
# ============================================================

CEDULAS_POR_CODIGO = {
    "MSL-0004-E": "604540452",
    "MSL-0005-E": "601890519",
    "MSL-0007-E": "604810789",
    "MSL-0003-E": "116140182",
    "MSL-0002-E": "111840704",
    "MSL-0001-E": "801100551",
}

# ============================================================
# SCRIPT
# ============================================================

def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:
        print("🛠️ Actualizando cédulas en tabla empleados...")

        for codigo, cedula in CEDULAS_POR_CODIGO.items():
            cur.execute(
                """
                UPDATE empleados
                SET cedula_id = %s
                WHERE codigo = %s
                """,
                (cedula, codigo)
            )

            print(f"   ✔ {codigo} → {cedula}")

        conn.commit()
        print("✅ Actualización completada correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante la actualización:")
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
