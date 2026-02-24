import psycopg2
from psycopg2 import sql

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def column_exists(cursor, table_name, column_name):
    cursor.execute("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = %s
        AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone() is not None


def add_column_if_not_exists(cursor, table_name, column_name):
    if not column_exists(cursor, table_name, column_name):
        print(f"➕ Agregando columna: {column_name}")
        cursor.execute(
            sql.SQL("ALTER TABLE {} ADD COLUMN {} TEXT").format(
                sql.Identifier(table_name),
                sql.Identifier(column_name)
            )
        )
    else:
        print(f"✔ La columna {column_name} ya existe.")


def main():
    conn = None
    try:
        print("🔌 Conectando a Railway...")
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        table_name = "draft_survey"

        columns_to_add = [
            "chief_officer",
            "master",
            "msl_surveyor"
        ]

        for column in columns_to_add:
            add_column_if_not_exists(cur, table_name, column)

        conn.commit()
        print("✅ Proceso finalizado correctamente.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ Error:", e)

    finally:
        if conn:
            conn.close()
            print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()