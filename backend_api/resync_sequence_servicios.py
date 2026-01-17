import psycopg2


DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    print("==============================================")
    print(" ERP-SOM | RESYNC SEQUENCE - TABLA SERVICIOS")
    print("==============================================")

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cur = conn.cursor()

        # -------------------------------------------------
        # 1️⃣ Obtener último consec real
        # -------------------------------------------------
        cur.execute("SELECT COALESCE(MAX(consec), 0) FROM servicios;")
        max_consec = cur.fetchone()[0]

        print(f"✔ Último consec detectado: {max_consec}")

        # -------------------------------------------------
        # 2️⃣ Sincronizar secuencia
        # -------------------------------------------------
        cur.execute("""
            SELECT setval(
                pg_get_serial_sequence('servicios', 'consec'),
                %s
            );
        """, (max_consec,))

        print("✔ Secuencia sincronizada correctamente")

        # -------------------------------------------------
        # 3️⃣ Verificar próximo valor
        # -------------------------------------------------
        cur.execute("SELECT nextval(pg_get_serial_sequence('servicios', 'consec'));")
        next_val = cur.fetchone()[0]

        print(f"✔ Próximo consec será: {next_val}")

        cur.close()
        conn.close()

        print("==============================================")
        print(" ✅ PROCESO COMPLETADO SIN ERRORES")
        print("==============================================")

    except Exception as e:
        print("❌ ERROR durante la sincronización:")
        print(str(e))


if __name__ == "__main__":
    main()
