import psycopg2
import sys


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # --------------------------------------------------
        # 1. Obtener último num_informe válido
        # --------------------------------------------------
        print("🔎 Buscando último num_informe...")
        cur.execute("""
            SELECT MAX(split_part(num_informe, '-', 1)::int)
            FROM servicios
            WHERE num_informe ~ '^[0-9]{4}-'
        """)
        row = cur.fetchone()
        ultimo = row[0] if row and row[0] else 2139

        print(f"📌 Último consecutivo encontrado: {ultimo}")

        # --------------------------------------------------
        # 2. Verificar si la secuencia existe
        # --------------------------------------------------
        print("🔎 Verificando secuencia...")
        cur.execute("""
            SELECT 1
            FROM pg_class
            WHERE relkind = 'S'
              AND relname = 'servicios_num_informe_seq'
        """)
        exists = cur.fetchone()

        if not exists:
            print("🆕 Secuencia NO existe. Creándola...")
            cur.execute(f"""
                CREATE SEQUENCE servicios_num_informe_seq
                START {ultimo + 1}
            """)
            print("✅ Secuencia creada correctamente.")
        else:
            print("♻️ Secuencia existe. Sincronizándola...")
            cur.execute("""
                SELECT setval(
                    'servicios_num_informe_seq',
                    %s
                )
            """, (ultimo,))
            print("✅ Secuencia sincronizada correctamente.")

        # --------------------------------------------------
        # 3. Verificación final
        # --------------------------------------------------
        cur.execute("SELECT nextval('servicios_num_informe_seq')")
        next_val = cur.fetchone()[0]

        print(f"🚀 nextval OK → {next_val}")

        cur.close()
        conn.close()
        print("🎉 Proceso finalizado SIN errores.")

    except Exception as e:
        print("❌ ERROR:")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
