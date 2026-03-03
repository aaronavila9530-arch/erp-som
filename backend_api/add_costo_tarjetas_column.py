import psycopg2


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def add_column():

    try:

        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        print("Conectado a PostgreSQL")

        # ============================================
        # Verificar si la columna ya existe
        # ============================================

        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='servicios'
            AND column_name='costo_tarjetas'
        """)

        exists = cur.fetchone()

        if exists:
            print("La columna costo_tarjetas ya existe.")
            return

        # ============================================
        # Crear columna
        # ============================================

        cur.execute("""
            ALTER TABLE servicios
            ADD COLUMN costo_tarjetas NUMERIC(12,2) DEFAULT 0
        """)

        print("Columna costo_tarjetas agregada correctamente.")

        cur.close()
        conn.close()

    except Exception as e:
        print("ERROR:", e)


if __name__ == "__main__":
    add_column()