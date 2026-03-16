import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE = "draft_survey_ballast"

def generate_columns():

    sql_commands = []

    for phase in ["init", "final"]:
        for i in range(1, 21):

            height_col = f"{phase}_fw_{i}_height"
            volume_col = f"{phase}_fw_{i}_volume"

            sql_commands.append(
                f'ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {height_col} NUMERIC;'
            )

            sql_commands.append(
                f'ALTER TABLE {TABLE} ADD COLUMN IF NOT EXISTS {volume_col} NUMERIC;'
            )

    return sql_commands


def main():

    print("Connecting to database...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True

    cursor = conn.cursor()

    commands = generate_columns()

    for sql in commands:
        print(sql)
        cursor.execute(sql)

    cursor.close()
    conn.close()

    print("\n✅ Fresh Water columns created successfully (up to 20 tanks).")


if __name__ == "__main__":
    main()