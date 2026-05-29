import os

import psycopg2


TABLE_NAME = "vessel_bunker_reports"
DB_URL = os.getenv("DATABASE_URL") or (
    "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT"
    "@tramway.proxy.rlwy.net:15258/railway?sslmode=require"
)


def main():
    print("Connecting to database...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        print("Searching *_dist_mtrs and *_gauge_mtrs columns...")

        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND (
                    column_name LIKE '%%_dist_mtrs'
                 OR column_name LIKE '%%_gauge_mtrs'
              )
            ORDER BY column_name
            """,
            (TABLE_NAME,),
        )

        columns = cur.fetchall()

        if not columns:
            print("No dist/gauge columns found.")
            return

        print(f"Found {len(columns)} columns")

        for col_name, data_type in columns:
            print(f"- {col_name} ({data_type})")

            if data_type == "text":
                print("  already TEXT, skipped")
                continue

            cur.execute(
                f"""
                ALTER TABLE {TABLE_NAME}
                ALTER COLUMN {col_name}
                TYPE TEXT
                USING {col_name}::TEXT
                """
            )
            print("  converted to TEXT")

        conn.commit()
        print("Bunker dist/gauge conversion completed.")

    except Exception as e:
        conn.rollback()
        print("Error:", str(e))
        raise

    finally:
        conn.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
