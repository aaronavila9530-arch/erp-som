import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        # -----------------------------------------------------
        # 1. CREAR COLUMNA usuario SI NO EXISTE
        # -----------------------------------------------------
        print("🧱 Verificando columna 'usuario' en empleados...")

        cur.execute("""
            ALTER TABLE empleados
            ADD COLUMN IF NOT EXISTS usuario TEXT;
        """)

        # -----------------------------------------------------
        # 2. ACTUALIZAR HORAS CONTRATADAS SEGÚN CODIGO
        # -----------------------------------------------------
        print("🕒 Actualizando horas_contratadas...")

        updates = {
            "MSL-0003-E": 160,
            "MSL-0002-E": 500,
            "MSL-0004-E": 150,
            "MSL-0005-E": 200,
            "MSL-0001-E": 500,
            "MSL-0007-E": 150,
            "MSL-0006-E": 160,
        }

        for codigo, horas in updates.items():
            cur.execute(
                """
                UPDATE empleados
                SET horas_contratadas = %s
                WHERE codigo = %s
                """,
                (horas, codigo)
            )

        conn.commit()
        print("✅ Cambios aplicados correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR. Se hizo ROLLBACK.")
        print(e)

    finally:
        cur.close()
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
