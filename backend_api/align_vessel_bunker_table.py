import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

NEW_COLUMNS = {
    "berthing_hour": "VARCHAR(2)",
    "berthing_minute": "VARCHAR(2)",
    "chief_engineer_name": "VARCHAR(150)",
    "owner_name": "VARCHAR(150)",
    "charterers_name": "VARCHAR(150)",
    "log_bunker_vlsfo": "NUMERIC",
    "log_bunker_hfso": "NUMERIC",
    "log_bunker_mdo": "NUMERIC",
    "log_bunker_lsmgo": "NUMERIC",
}

def column_exists(cursor, table, column):
    cursor.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name=%s AND column_name=%s
    """, (table, column))
    return cursor.fetchone() is not None


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    table = "vessel_bunker_reports"

    for col, col_type in NEW_COLUMNS.items():
        if not column_exists(cur, table, col):
            print(f"Adding column: {col}")
            cur.execute(f"""
                ALTER TABLE {table}
                ADD COLUMN {col} {col_type};
            """)
        else:
            print(f"Column already exists: {col}")

    cur.close()
    conn.close()
    print("✔ Table aligned successfully.")


if __name__ == "__main__":
    main()