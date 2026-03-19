import psycopg2

# =========================================================
# CONFIG
# =========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

EMPLEADO_ID = 1
USUARIO = "admin"

# =========================================================
# MAIN
# =========================================================
def main():
    conn = None
    try:
        print("🔌 Conectando a la base de datos...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # ================= BEFORE =================
        cur.execute(
            "SELECT id, nombre, usuario FROM empleados WHERE id = %s",
            (EMPLEADO_ID,)
        )
        before = cur.fetchone()

        if not before:
            print("❌ No existe el empleado con ese ID")
            return

        print(f"📌 ANTES → ID={before[0]} | Nombre={before[1]} | Usuario={before[2]}")

        # ================= UPDATE =================
        cur.execute(
            """
            UPDATE empleados
            SET usuario = %s
            WHERE id = %s
            RETURNING id, nombre, usuario
            """,
            (USUARIO, EMPLEADO_ID)
        )

        after = cur.fetchone()
        conn.commit()

        print(f"✅ DESPUÉS → ID={after[0]} | Nombre={after[1]} | Usuario={after[2]}")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:", str(e))

    finally:
        if conn:
            conn.close()
            print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()