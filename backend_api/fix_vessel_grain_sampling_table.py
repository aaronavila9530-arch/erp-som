import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

REQUIRED_COLUMNS = {
    "cert_no": "TEXT",
    "place_date": "DATE",
    "vessel_name": "TEXT",
    "requested_by": "TEXT",
    "captain": "TEXT",
    "chief_officer": "TEXT",
    "arrival_buoy_time": "TIMESTAMP",
    "nor_tendered_time": "TIMESTAMP",
    "holds_opening_time": "TIMESTAMP",
    "sampling_start_time": "TIMESTAMP",
    "sampling_end_time": "TIMESTAMP",
    "products": "JSONB",
    "products_total": "TEXT",
    "supervision": "TIMESTAMP",
    "conclusion": "TEXT",
    "created_at": "TIMESTAMP DEFAULT NOW()",
    "updated_at": "TIMESTAMP DEFAULT NOW()"
}

# Columnas que ya NO usas
OBSOLETE_COLUMNS = [
    "purpose",
    "arrival_info",
    "inspection_info",
    "flag_port",
    "grt",
    "nrt",
    "imo",
    "build_year",
    "sampling",
    "procedure",
    "surveyors_onboard_time",
    "seals_verification_time",
    "surveyors_disembark_time",
    "products_header_line",
    "legal_text",
    "attachments",
    "surveyor_name",
    "surveyor_position"
]

TABLE = "vessel_grain_sampling_reports"


def column_exists(cur, column_name):
    cur.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (TABLE, column_name))
    return cur.fetchone() is not None


def main():
    print("Connecting to DB...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    print("Checking required columns...")

    for column, col_type in REQUIRED_COLUMNS.items():
        if not column_exists(cur, column):
            print(f"Adding column: {column}")
            cur.execute(
                f'ALTER TABLE {TABLE} ADD COLUMN {column} {col_type};'
            )
        else:
            print(f"Column exists: {column}")

    print("\nRemoving obsolete columns...")

    for column in OBSOLETE_COLUMNS:
        if column_exists(cur, column):
            print(f"Dropping column: {column}")
            cur.execute(
                f'ALTER TABLE {TABLE} DROP COLUMN {column} CASCADE;'
            )
        else:
            print(f"Column already removed: {column}")

    print("\nEnsuring products is JSONB...")
    cur.execute(f"""
        ALTER TABLE {TABLE}
        ALTER COLUMN products TYPE JSONB
        USING products::jsonb;
    """)

    print("\nTable aligned successfully.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
