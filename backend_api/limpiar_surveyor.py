import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        print("🧹 Limpiando tabla surveyor...")

        cur.execute("""
            TRUNCATE TABLE surveyor
            RESTART IDENTITY
            CASCADE;
        """)

        conn.commit()
        print("✅ Tabla surveyor limpiada correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante la limpieza:")
        print(e)

    finally:
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
