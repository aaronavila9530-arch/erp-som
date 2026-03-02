import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE_NAME = "vessel_cargo_condition_surveys"

ALTER_SQL = f"""
ALTER TABLE {TABLE_NAME}
ADD COLUMN status TEXT DEFAULT 'Draft';
"""

def main():
    conn = None
    cur = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        conn.autocommit = False
        cur = conn.cursor()

        print("Adding column 'status'...")
        cur.execute(ALTER_SQL)

        conn.commit()
        print("✅ Column 'status' added successfully.")

    except Exception as e:
        print("❌ Error:", e)
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()