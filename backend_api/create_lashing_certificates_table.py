import psycopg2

# =========================================================
# DATABASE CONNECTION
# =========================================================

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# =========================================================
# CREATE TABLE SCRIPT
# =========================================================

SQL = """
CREATE TABLE IF NOT EXISTS lashing_certificates (

    id SERIAL PRIMARY KEY,

    report_no TEXT,
    customer TEXT,
    port TEXT,
    country TEXT,

    flat_rack_container TEXT,
    cargo_type TEXT,
    lashing_material TEXT,
    place TEXT,

    date TEXT,

    ratchet_quantity INTEGER,
    where_carry_out TEXT,
    completion_date TEXT,

    status TEXT DEFAULT 'draft'

);
"""

# =========================================================
# EXECUTION
# =========================================================

def main():

    try:

        print("Connecting to Railway PostgreSQL...")

        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True

        cur = conn.cursor()

        print("Creating table lashing_certificates...")

        cur.execute(SQL)

        cur.close()
        conn.close()

        print("SUCCESS: Table created or already exists.")

    except Exception as e:

        print("ERROR:", e)


if __name__ == "__main__":
    main()