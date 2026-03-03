import psycopg2
from psycopg2 import sql

# ==========================================================
# CONFIG
# ==========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"
TABLE_NAME = "vessel_grain_sampling_reports"

COLUMNS_TO_REMOVE = [
    "vessel_port_registry_flag",
    "vessel_grt",
    "vessel_nrt",
    "vessel_imo_no",
    "vessel_year_build",
]


# ==========================================================
# MAIN
# ==========================================================
def main():

    print("🔎 Connecting to database...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        print(f"📋 Removing columns from table: {TABLE_NAME}")

        for col_name in COLUMNS_TO_REMOVE:

            print(f"➖ Dropping column (if exists): {col_name}")

            alter_query = sql.SQL("""
                ALTER TABLE {}
                DROP COLUMN IF EXISTS {}
            """).format(
                sql.Identifier(TABLE_NAME),
                sql.Identifier(col_name)
            )

            cur.execute(alter_query)

        conn.commit()
        print("✅ Columns removed successfully.")

    except Exception as e:
        conn.rollback()
        print("❌ Error:", e)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()