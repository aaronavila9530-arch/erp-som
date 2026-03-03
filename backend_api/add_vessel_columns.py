import psycopg2
from psycopg2 import sql

# ==========================================================
# CONFIG
# ==========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"
TABLE_NAME = "vessel_cargo_condition_surveys"

NEW_COLUMNS = {
    "vessel_port_registry_flag": "TEXT",
    "vessel_grt": "TEXT",
    "vessel_nrt": "TEXT",
    "vessel_imo_no": "TEXT",
    "vessel_year_build": "TEXT",
}


# ==========================================================
# MAIN
# ==========================================================
def main():

    print("🔎 Connecting to database...")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    try:

        # Get existing columns
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
        """, (TABLE_NAME,))

        existing_columns = {row[0] for row in cur.fetchall()}

        print(f"📋 Existing columns found: {len(existing_columns)}")

        for col_name, col_type in NEW_COLUMNS.items():

            if col_name in existing_columns:
                print(f"✔ Column already exists: {col_name}")
                continue

            print(f"➕ Adding column: {col_name}")

            alter_query = sql.SQL("""
                ALTER TABLE {} 
                ADD COLUMN {} {}
            """).format(
                sql.Identifier(TABLE_NAME),
                sql.Identifier(col_name),
                sql.SQL(col_type)
            )

            cur.execute(alter_query)

        conn.commit()
        print("✅ Done successfully.")

    except Exception as e:
        conn.rollback()
        print("❌ Error:", e)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()