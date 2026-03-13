import psycopg2


# =========================================================
# DATABASE CONNECTION
# =========================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


# =========================================================
# CREATE COLUMN
# =========================================================

def create_column():

    conn = None

    try:

        print("Connecting to database...")

        conn = psycopg2.connect(DATABASE_URL)

        cur = conn.cursor()

        # ---------------------------------------------
        # CHECK IF COLUMN EXISTS
        # ---------------------------------------------

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='vessel_holds_inspection_certificates'
            AND column_name='master_chief_officer'
        """)

        exists = cur.fetchone()

        if exists:

            print("Column 'master_chief_officer' already exists.")
            return

        # ---------------------------------------------
        # CREATE COLUMN
        # ---------------------------------------------

        print("Creating column 'master_chief_officer'...")

        cur.execute("""
            ALTER TABLE vessel_holds_inspection_certificates
            ADD COLUMN master_chief_officer TEXT
        """)

        conn.commit()

        print("Column created successfully.")

    except Exception as e:

        if conn:
            conn.rollback()

        print("ERROR:", e)

    finally:

        if conn:
            conn.close()

        print("Done.")


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    create_column()