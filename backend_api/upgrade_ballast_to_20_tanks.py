import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def column_exists(cur, table, column):
    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
        AND column_name = %s
    """, (table, column))
    return cur.fetchone() is not None


def add_column_if_not_exists(cur, table, column, col_type):
    if not column_exists(cur, table, column):
        print(f"➕ Adding column: {column}")
        cur.execute(f'ALTER TABLE {table} ADD COLUMN "{column}" {col_type};')
    else:
        print(f"✔ Column already exists: {column}")


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    table = "draft_survey_ballast"

    try:

        for phase in ["init", "final"]:

            for tank_num in range(6, 21):  # 6 → 20

                for side in ["p", "s"]:  # Port / Starboard

                    base = f"{phase}_wbt_{tank_num}{side}"

                    add_column_if_not_exists(cur, table, f"{base}_sounding", "NUMERIC(12,4)")
                    add_column_if_not_exists(cur, table, f"{base}_volume", "NUMERIC(14,4)")
                    add_column_if_not_exists(cur, table, f"{base}_density", "NUMERIC(10,6)")

        conn.commit()
        print("\n✅ Upgrade complete: Table now supports up to 20 WBT tanks.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR:", e)

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()