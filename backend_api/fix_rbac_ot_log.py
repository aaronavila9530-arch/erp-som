import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def main():
    conn = None

    try:
        print("🔌 Conectando...")

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print("🛠 Insertando permiso faltante...")

        cur.execute("""
            INSERT INTO rbac_permissions (role_code, module, action, allowed)
            VALUES ('user', 'hhrr', 'ot_log', TRUE)
            ON CONFLICT (role_code, module, action)
            DO UPDATE SET allowed = TRUE;
        """)

        conn.commit()

        print("✅ Permiso creado correctamente")

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