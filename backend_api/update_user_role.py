import psycopg2

# =========================================================
# 🔗 CONNECTION STRING (TU DB)
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# =========================================================
# 🎯 DATA
# =========================================================
USUARIO = "aaron01"
NEW_ROLE = "user"

# =========================================================
# 🚀 EXECUTE
# =========================================================
def main():
    try:
        print("🔌 Conectando a la base de datos...")

        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        print(f"✏️ Actualizando rol de '{USUARIO}' → '{NEW_ROLE}'...")

        cur.execute("""
            UPDATE usuarios
            SET rol = %s
            WHERE LOWER(usuario) = LOWER(%s)
            RETURNING usuario, rol
        """, (NEW_ROLE, USUARIO))

        row = cur.fetchone()

        if not row:
            print(f"⚠️ Usuario '{USUARIO}' no encontrado.")
            conn.rollback()
            return

        conn.commit()

        print("✅ Actualización exitosa:")
        print(f"   Usuario: {row[0]}")
        print(f"   Nuevo rol: {row[1]}")

    except Exception as e:
        print("❌ ERROR:", str(e))

    finally:
        try:
            cur.close()
            conn.close()
            print("🔒 Conexión cerrada.")
        except:
            pass


if __name__ == "__main__":
    main()