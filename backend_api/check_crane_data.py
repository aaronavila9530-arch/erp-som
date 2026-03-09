import psycopg2
from psycopg2.extras import RealDictCursor

# ==========================================================
# DATABASE CONNECTION
# ==========================================================

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# ==========================================================
# MAIN
# ==========================================================

def main():

    print("\nConnecting to database...\n")

    conn = psycopg2.connect(DB_URL)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT *
        FROM vessel_crane_inspection_reports
        ORDER BY id
    """)

    rows = cur.fetchall()

    if not rows:
        print("No records found.")
        return

    print(f"Total records: {len(rows)}\n")

    for r in rows:

        rid = r["id"]

        print("======================================")
        print(f"REPORT ID: {rid}")
        print("======================================")

        # --------------------------------------------------
        # CRANE REMARKS
        # --------------------------------------------------

        print("\nCRANE REMARKS:")

        for crane in range(1,5):

            for i in range(1,11):

                key = f"crane{crane}_remark_{i}"

                val = r.get(key)

                if val:
                    print(f"{key} = {val}")

        # --------------------------------------------------
        # RECOMMENDATIONS
        # --------------------------------------------------

        print("\nRECOMMENDATIONS:")

        for i in range(1,11):

            key = f"recommendation_{i}"

            val = r.get(key)

            if val:
                print(f"{key} = {val}")

        # --------------------------------------------------
        # GRABS CONDITION
        # --------------------------------------------------

        print("\nGRABS CONDITION:")

        for i in range(1,11):

            key = f"grabs_condition_{i}"

            val = r.get(key)

            if val:
                print(f"{key} = {val}")

        # --------------------------------------------------
        # CONCLUSION
        # --------------------------------------------------

        print("\nCONCLUSION:")

        for i in range(1,21):

            key = f"conclusion_{i}"

            val = r.get(key)

            if val:
                print(f"{key} = {val}")

        print("\n")

    conn.close()

    print("\nDone.\n")


# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()