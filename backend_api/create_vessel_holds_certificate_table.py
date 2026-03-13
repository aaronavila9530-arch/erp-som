import psycopg2


DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def create_table():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    cur.execute("""

    CREATE TABLE IF NOT EXISTS vessel_holds_inspection_certificates (

        id SERIAL PRIMARY KEY,

        -- =====================================================
        -- REPORT HEADER
        -- =====================================================

        report_number TEXT,
        port TEXT,
        country TEXT,

        -- =====================================================
        -- CERTIFICATE HEADER
        -- =====================================================

        vessel TEXT,
        voyage TEXT,
        load_port TEXT,
        place TEXT,
        installation TEXT,
        product TEXT,
        date TEXT,

        -- =====================================================
        -- SURVEY INFORMATION
        -- =====================================================

        inspection_time TEXT,
        vessel_holds TEXT,
        vessel_holds_status TEXT,

        -- =====================================================
        -- CARGO
        -- =====================================================

        cargo_holds TEXT,
        accepted_time TEXT,

        -- =====================================================
        -- LOCATION
        -- =====================================================

        place_location TEXT,
        place_date TEXT,

        -- =====================================================
        -- HOSE TEST
        -- =====================================================

        hose_test_start TEXT,
        hose_test_end TEXT,

        -- =====================================================
        -- REMARKS
        -- =====================================================

        remarks TEXT,

        -- =====================================================
        -- SYSTEM
        -- =====================================================

        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        status TEXT DEFAULT 'draft'

    );

    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Table vessel_holds_inspection_certificates created successfully.")


if __name__ == "__main__":
    create_table()