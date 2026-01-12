import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        with conn.cursor() as cur:
            print("🔎 Verificando si existe columna horas_contratadas en empleados...")

            cur.execute("""
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'empleados'
                  AND column_name = 'horas_contratadas'
                LIMIT 1
            """)
            exists = cur.fetchone() is not None

            if exists:
                print("✅ La columna horas_contratadas ya existe. No se realizaron cambios.")
                conn.rollback()
                return

            print("🛠️ Creando columna horas_contratadas...")
            cur.execute("""
                ALTER TABLE empleados
                ADD COLUMN horas_contratadas NUMERIC(10,2) NOT NULL DEFAULT 0
            """)

            conn.commit()
            print("✅ Columna horas_contratadas creada exitosamente (NUMERIC(10,2) DEFAULT 0).")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)
        raise
    finally:
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
