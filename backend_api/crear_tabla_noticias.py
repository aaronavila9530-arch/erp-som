# crear_tabla_noticias.py
import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

def main():
    print("🔌 Conectando a PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("📰 Creando tabla noticias...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS noticias (
            id SERIAL PRIMARY KEY,
            noticia_1 TEXT,
            noticia_2 TEXT,
            noticia_3 TEXT,
            noticia_4 TEXT,
            noticia_5 TEXT,
            created_by VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla noticias creada correctamente.")

if __name__ == "__main__":
    main()
