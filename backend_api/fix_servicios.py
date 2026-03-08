import psycopg2

# ============================================================
# CONFIG
# ============================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# ============================================================
# MAIN
# ============================================================

def run():

    conn = None

    try:

        print("Conectando a Railway PostgreSQL...")

        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False

        cur = conn.cursor()

        # ------------------------------------------------------
        # UPDATE 416
        # ------------------------------------------------------

        cur.execute("""
            UPDATE servicios
            SET num_informe = %s
            WHERE consec = %s
        """, ("2159-0203-2026", 416))

        print("✔ consec 416 actualizado")

        # ------------------------------------------------------
        # UPDATE 415
        # ------------------------------------------------------

        cur.execute("""
            UPDATE servicios
            SET num_informe = %s
            WHERE consec = %s
        """, ("2158-0203-2026", 415))

        print("✔ consec 415 actualizado")

        # ------------------------------------------------------
        # UPDATE 418
        # ------------------------------------------------------

        cur.execute("""
            UPDATE servicios
            SET puerto = %s
            WHERE consec = %s
        """, ("Pisco", 418))

        print("✔ consec 418 puerto actualizado")

        conn.commit()

        print("\n✅ Cambios aplicados correctamente.")

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ ERROR:", str(e))

    finally:

        if conn:
            conn.close()
            print("Conexión cerrada.")


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    run()