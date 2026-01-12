import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("🔧 Conectado a PostgreSQL (Railway)")

    cur.execute("""
        ALTER TABLE hr_ot_log
        ADD COLUMN IF NOT EXISTS estado VARCHAR(15) NOT NULL DEFAULT 'PENDIENTE'
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Columna 'estado' creada correctamente en hr_ot_log")

if __name__ == "__main__":
    main()
