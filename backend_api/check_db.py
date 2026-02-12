import os
import psycopg2
from urllib.parse import urlparse

# 1️⃣ Copia aquí EXACTAMENTE tu DATABASE_URL desde Railway
DATABASE_URL = "postgresql://postgres:PTAibTyVSzdowUdBFZhqrxCWicNmdFOr@postgres.railway.internal:5432/railway"

print("\n=== PARSING DATABASE URL ===")
parsed = urlparse(DATABASE_URL)

print("Scheme:", parsed.scheme)
print("Host:", parsed.hostname)
print("Port:", parsed.port)
print("User:", parsed.username)
print("Database:", parsed.path.lstrip("/"))

print("\n=== CONNECTING... ===")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("SELECT current_database();")
print("Current database:", cur.fetchone()[0])

cur.execute("SELECT current_user;")
print("Current user:", cur.fetchone()[0])

cur.execute("SHOW search_path;")
print("Search path:", cur.fetchone()[0])

print("\n=== TABLES FOUND ===")
cur.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY table_schema, table_name;
""")

tables = cur.fetchall()

if not tables:
    print("No tables found.")
else:
    for schema, table in tables:
        print(f"{schema}.{table}")

cur.close()
conn.close()

print("\n=== DONE ===")
