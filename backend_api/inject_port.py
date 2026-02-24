import psycopg2
from psycopg2 import sql


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def inject_port():
    try:
        print("🔌 Conectando a base de datos...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False

        cursor = conn.cursor()

        # =====================================================
        # VALIDAR SI YA EXISTE
        # =====================================================
        check_query = """
            SELECT id
            FROM continentes_paises_puertos
            WHERE continente = %s
              AND pais = %s
              AND puerto = %s
        """

        cursor.execute(
            check_query,
            ("América", "Chile", "Caleta Patillos")
        )

        existing = cursor.fetchone()

        if existing:
            print("⚠️ El puerto ya existe con ID:", existing[0])
        else:
            # =====================================================
            # INSERTAR NUEVO PUERTO
            # =====================================================
            insert_query = """
                INSERT INTO continentes_paises_puertos
                (continente, pais, puerto)
                VALUES (%s, %s, %s)
                RETURNING id
            """

            cursor.execute(
                insert_query,
                ("América", "Chile", "Caleta Patillos")
            )

            new_id = cursor.fetchone()[0]
            conn.commit()

            print("✅ Puerto insertado correctamente.")
            print("🆔 Nuevo ID:", new_id)

        cursor.close()
        conn.close()
        print("🔒 Conexión cerrada.")

    except Exception as e:
        print("❌ Error:", e)


if __name__ == "__main__":
    inject_port()