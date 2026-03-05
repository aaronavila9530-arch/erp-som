import psycopg2


DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():

    try:

        print("Connecting to database...")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("Connected.\n")

        # -------------------------------------------------------
        # CHECK IF COLUMN EXISTS
        # -------------------------------------------------------

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'vessel_crane_inspection_reports'
            AND column_name = 'status'
        """)

        exists = cur.fetchone()

        if exists:
            print("Column 'status' already exists. Nothing to do.")
            conn.close()
            return

        # -------------------------------------------------------
        # ADD COLUMN
        # -------------------------------------------------------

        print("Creating column 'status'...")

        cur.execute("""
            ALTER TABLE vessel_crane_inspection_reports
            ADD COLUMN status TEXT
        """)

        conn.commit()

        print("Column 'status' created successfully.")

        conn.close()

    except Exception as e:

        print("ERROR:", str(e))


if __name__ == "__main__":
    main()