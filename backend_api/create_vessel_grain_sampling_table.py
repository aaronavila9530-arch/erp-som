import psycopg2
from psycopg2 import sql


DB_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)


DDL = """
CREATE TABLE IF NOT EXISTS vessel_grain_sampling_reports (

    -- =========================
    -- PRIMARY KEY & METADATA
    -- =========================
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- =========================
    -- HEADER
    -- =========================
    cert_no TEXT,
    place_date TEXT,

    -- =========================
    -- INTRODUCCIÓN
    -- =========================
    purpose TEXT,

    -- =========================
    -- INSTRUCCIONES
    -- =========================
    requested_by TEXT,
    arrival_info TEXT,
    inspection_info TEXT,
    captain TEXT,
    chief_officer TEXT,

    -- =========================
    -- BUQUE
    -- =========================
    vessel_name TEXT,
    flag_port TEXT,
    grt TEXT,
    nrt TEXT,
    imo TEXT,
    build_year TEXT,

    -- =========================
    -- TIEMPOS
    -- =========================
    times TEXT,

    -- =========================
    -- PRODUCTOS
    -- =========================
    products_summary TEXT,
    products_table TEXT,

    -- =========================
    -- SUPERVISIÓN
    -- =========================
    supervision TEXT,

    -- =========================
    -- TOMA DE MUESTRAS
    -- =========================
    sampling TEXT,

    -- =========================
    -- PROCEDIMIENTO
    -- =========================
    procedure TEXT,

    -- =========================
    -- CONCLUSIÓN
    -- =========================
    conclusion TEXT
);
"""


def main():
    print("🔧 Connecting to PostgreSQL...")
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            print("🧱 Creating table vessel_grain_sampling_reports ...")
            cur.execute(DDL)
            print("✅ Table created successfully (or already exists).")
    finally:
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
