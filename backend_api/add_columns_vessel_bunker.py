import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

ALTER_STATEMENTS = [
    "ADD COLUMN IF NOT EXISTS antecedent_arrived_port TEXT",
    "ADD COLUMN IF NOT EXISTS log_eosp_date DATE",
    "ADD COLUMN IF NOT EXISTS log_pob_date DATE",
    "ADD COLUMN IF NOT EXISTS log_fwe_date DATE",
    "ADD COLUMN IF NOT EXISTS log_bunker_date DATE",
    "ADD COLUMN IF NOT EXISTS log_at_survey_date DATE",
    "ADD COLUMN IF NOT EXISTS surveyor_name TEXT",
    "ADD COLUMN IF NOT EXISTS master_name TEXT"
]

def main():
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False

        cur = conn.cursor()

        for stmt in ALTER_STATEMENTS:
            query = sql.SQL("ALTER TABLE vessel_bunker_reports {}").format(
                sql.SQL(stmt)
            )
            print(f"Executing: {stmt}")
            cur.execute(query)

        conn.commit()
        print("✅ Columns added successfully.")

    except Exception as e:
        print("❌ Error:", e)
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()