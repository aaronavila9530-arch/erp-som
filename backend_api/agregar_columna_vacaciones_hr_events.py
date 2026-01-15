import psycopg2
from psycopg2 import sql

# ============================================================
# CONFIGURACIÓN DE CONEXIÓN
# ============================================================
DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        print("📋 Verificando columna 'vacaciones' en tabla hr_events...")

        cur.execute("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'hr_events'
              AND column_name = 'vacaciones'
        """)

        exists = cur.fetchone()

        if exists:
            print("ℹ️ La columna 'vacaciones' ya existe. No se realiza ningún cambio.")
        else:
            print("➕ Agregando columna 'vacaciones' a hr_events...")

            cur.execute("""
                ALTER TABLE hr_events
                ADD COLUMN vacaciones NUMERIC(6,2)
            """)

            conn.commit()
            print("✅ Columna 'vacaciones' agregada correctamente.")

        cur.close()
        conn.close()
        print("🔒 Conexión cerrada.")

    except Exception as e:
        print("❌ ERROR al modificar la tabla hr_events")
        print(str(e))
        try:
            conn.rollback()
        except Exception:
            pass


if __name__ == "__main__":
    main()
