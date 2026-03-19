import psycopg2
from psycopg2.extras import RealDictCursor


# =========================================================
# 🔗 CONNECTION STRING (TU DB)
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    conn = None

    try:
        print("🔌 Conectando a la base de datos...")

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("🔍 Ejecutando query RBAC...")

        cur.execute("""
            SELECT *
            FROM rbac_permissions
            WHERE role_code = 'user'
              AND module = 'hhrr'
              AND action = 'ot_log';
        """)

        rows = cur.fetchall()

        if not rows:
            print("❌ NO EXISTE el permiso → user / hhrr / ot_log")
        else:
            print("✅ PERMISO ENCONTRADO:\n")
            for r in rows:
                print(r)

    except Exception as e:
        print("❌ ERROR:", str(e))

    finally:
        if conn:
            conn.close()
            print("\n🔒 Conexión cerrada")


if __name__ == "__main__":
    main()