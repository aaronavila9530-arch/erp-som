import psycopg2

OLD_PASSWORD = "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
NEW_PASSWORD = "IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT"

conn = psycopg2.connect(
    f"postgresql://postgres:{OLD_PASSWORD}@tramway.proxy.rlwy.net:15258/railway?sslmode=require"
)

cur = conn.cursor()
cur.execute(f"ALTER USER postgres WITH PASSWORD '{NEW_PASSWORD}';")
conn.commit()

print("✅ Password actualizada correctamente")

cur.close()
conn.close()
