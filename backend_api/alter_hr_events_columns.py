import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("🧱 Alterando tabla hr_events...")

        # -----------------------------------------------------
        # 1️⃣ AGREGAR COLUMNAS NUEVAS
        # -----------------------------------------------------
        cur.execute("""
            ALTER TABLE hr_events
            ADD COLUMN IF NOT EXISTS empleado TEXT,
            ADD COLUMN IF NOT EXISTS comentario_solicitud TEXT,
            ADD COLUMN IF NOT EXISTS comentario_apro_rech TEXT;
        """)
        print("✅ Columnas agregadas (si no existían)")

        # -----------------------------------------------------
        # 2️⃣ ELIMINAR COLUMNA empleado_id
        # -----------------------------------------------------
        cur.execute("""
            ALTER TABLE hr_events
            DROP COLUMN IF EXISTS empleado_id;
        """)
        print("🗑️ Columna empleado_id eliminada (si existía)")

        conn.commit()
        print("🎉 Cambios aplicados correctamente")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante la alteración de la tabla")
        print(str(e))

    finally:
        cur.close()
        conn.close()
        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()
