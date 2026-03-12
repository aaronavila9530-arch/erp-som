import psycopg2


# =========================================================
# DATABASE CONNECTION
# =========================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


# =========================================================
# CREATE TABLE
# =========================================================

SQL = """

CREATE TABLE IF NOT EXISTS weight_certificates (

    id SERIAL PRIMARY KEY,

    -- HEADER
    report_number TEXT,
    continent TEXT,
    country TEXT,
    port TEXT,
    operation TEXT,

    -- CERTIFICATE DATA
    vessel TEXT,
    voyage TEXT,
    commodity TEXT,
    bl_figure NUMERIC,
    cargo_hold TEXT,
    shipper TEXT,
    consignee TEXT,
    terminal TEXT,
    loading_port TEXT,
    weight_determination TEXT,
    date TEXT,

    -- QUANTITY
    quantity NUMERIC,

    -- REMARKS
    remarks TEXT,

    -- CONTROL
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    status TEXT DEFAULT 'draft'

);

"""


# =========================================================
# EXECUTE
# =========================================================

def main():

    print("Connecting to database...")

    conn = psycopg2.connect(DATABASE_URL)

    cursor = conn.cursor()

    print("Creating table weight_certificates...")

    cursor.execute(SQL)

    conn.commit()

    cursor.close()
    conn.close()

    print("Table created successfully.")


# =========================================================

if __name__ == "__main__":
    main()