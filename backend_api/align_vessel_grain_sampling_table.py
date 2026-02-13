import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


def run():

    print("🔧 Connecting to Railway DB...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        print("🔍 Aligning vessel_grain_sampling_reports table...")

        # =====================================================
        # ADD MISSING COLUMNS (SAFE MODE)
        # =====================================================

        alter_statements = [

            # HEADER
            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS requested_by TEXT;
            """,

            # TIMES (si faltan)
            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS arrival_buoy_time TIMESTAMP;
            """,

            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS nor_tendered_time TIMESTAMP;
            """,

            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS holds_opening_time TIMESTAMP;
            """,

            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS sampling_start_time TIMESTAMP;
            """,

            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS sampling_end_time TIMESTAMP;
            """,

            # PRODUCTS STRUCTURE
            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS products JSONB;
            """,

            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS products_total TEXT;
            """,

            # SUPERVISION
            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS supervision TIMESTAMP;
            """,

            # CONCLUSION
            """
            ALTER TABLE vessel_grain_sampling_reports
            ADD COLUMN IF NOT EXISTS conclusion TEXT;
            """,
        ]

        for stmt in alter_statements:
            cur.execute(stmt)

        conn.commit()

        print("✅ Table aligned successfully.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)

    finally:
        cur.close()
        conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    run()
