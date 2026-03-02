import psycopg2
from psycopg2 import sql


# =========================================================
# CONFIG
# =========================================================
DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"
TABLE_NAME = "vessel_cargo_condition_surveys"
COLUMN_NAME = "cargo_type"


# =========================================================
# MAIN
# =========================================================
def main():
    conn = None
    cur = None

    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        # -----------------------------------------------------
        # CHECK IF COLUMN EXISTS
        # -----------------------------------------------------
        print("🔍 Checking if column already exists...")

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name = %s
        """, (TABLE_NAME, COLUMN_NAME))

        exists = cur.fetchone()

        if exists:
            print(f"⚠ Column '{COLUMN_NAME}' already exists.")
        else:
            print(f"➕ Creating column '{COLUMN_NAME}'...")

            cur.execute(
                sql.SQL("ALTER TABLE {} ADD COLUMN {} TEXT").format(
                    sql.Identifier(TABLE_NAME),
                    sql.Identifier(COLUMN_NAME)
                )
            )

            conn.commit()
            print("✅ Column created successfully.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:", str(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()