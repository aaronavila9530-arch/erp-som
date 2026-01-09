import psycopg2
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"
)

SQL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS hr_events (
    id SERIAL PRIMARY KEY,

    empleado_id INTEGER NOT NULL
        REFERENCES empleados(id),

    event_type VARCHAR(40) NOT NULL,

    event_date DATE NOT NULL,

    period_year INTEGER,
    period_month INTEGER,

    status VARCHAR(20) DEFAULT 'PENDING',

    payload JSONB NOT NULL,

    created_by VARCHAR(50),
    approved_by VARCHAR(50),

    created_at TIMESTAMP DEFAULT now(),
    approved_at TIMESTAMP
);
"""

def main():
    print("🔌 Conectando a PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🧱 Creando tabla hr_events...")
    cur.execute(SQL_CREATE_TABLE)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla hr_events creada correctamente.")

if __name__ == "__main__":
    main()
