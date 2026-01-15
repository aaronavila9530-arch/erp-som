import psycopg2
from psycopg2 import sql

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def column_exists(cursor, table, column):
    cursor.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
          AND column_name = %s
    """, (table, column))
    return cursor.fetchone() is not None


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        # =====================================================
        # AGREGAR fecha_nacimiento
        # =====================================================
        if not column_exists(cur, "empleados", "fecha_nacimiento"):
            print("➕ Agregando columna fecha_nacimiento (DATE)...")
            cur.execute("""
                ALTER TABLE empleados
                ADD COLUMN fecha_nacimiento DATE
            """)
        else:
            print("ℹ️  Columna fecha_nacimiento ya existe")

        # =====================================================
        # AGREGAR edad
        # =====================================================
        if not column_exists(cur, "empleados", "edad"):
            print("➕ Agregando columna edad (INTEGER)...")
            cur.execute("""
                ALTER TABLE empleados
                ADD COLUMN edad INTEGER
            """)
        else:
            print("ℹ️  Columna edad ya existe")

        # =====================================================
        # CALCULAR EDAD (SI HAY FECHA)
        # =====================================================
        print("🔄 Calculando edad a partir de fecha_nacimiento...")
        cur.execute("""
            UPDATE empleados
            SET edad = DATE_PART('year', AGE(CURRENT_DATE, fecha_nacimiento))
            WHERE fecha_nacimiento IS NOT NULL
        """)

        conn.commit()
        print("✅ Migración completada correctamente")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR DURANTE LA MIGRACIÓN")
        print(str(e))
        raise

    finally:
        cur.close()
        conn.close()
        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()
