import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway?sslmode=require"

try:
    # Conexión
    conn = psycopg2.connect(DB_URL)
    print("✅ Conectado correctamente\n")

    # Cursor
    cur = conn.cursor()
    cur.execute("""
        SELECT table_schema, table_name
        FROM information_schema.tables
        WHERE table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name;
    """)

    tables = cur.fetchall()

    if not tables:
        print("⚠️ NO EXISTEN TABLAS EN ESTA BASE")
    else:
        print("📦 TABLAS ENCONTRADAS:\n")
        for schema, name in tables:
            print(f"{schema}.{name}")

    cur.close()
    conn.close()

except Exception as e:
    print("❌ Error:")
    print(e)
