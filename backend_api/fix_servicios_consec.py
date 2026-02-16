import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# CONEXIÓN RAILWAY
# ============================================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


def main():

    print("🔌 Connecting to Railway PostgreSQL...")

    conn = None
    cur = None

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("✅ Connected successfully.\n")

        # ====================================================
        # UPDATE consec = 404
        # ====================================================
        print("🔄 Updating consec 404...")

        cur.execute("""
            UPDATE servicios
            SET
                estado = %s,
                num_informe = NULL
            WHERE consec = %s
            RETURNING consec, estado, num_informe
        """, ("Confirmado", 404))

        row_404 = cur.fetchone()

        if row_404:
            print("✔ consec 404 updated:")
            print(row_404)
        else:
            print("⚠ No record found with consec = 404")

        print()

        # ====================================================
        # UPDATE consec = 406
        # ====================================================
        print("🔄 Updating consec 406...")

        cur.execute("""
            UPDATE servicios
            SET
                estado = %s,
                num_informe = %s
            WHERE consec = %s
            RETURNING consec, estado, num_informe
        """, ("En Operación", "2151-1102-2026", 406))

        row_406 = cur.fetchone()

        if row_406:
            print("✔ consec 406 updated:")
            print(row_406)
        else:
            print("⚠ No record found with consec = 406")

        print()

        # ====================================================
        # COMMIT
        # ====================================================
        conn.commit()
        print("💾 Changes committed successfully.")

    except Exception as e:
        print("❌ ERROR:", str(e))
        if conn:
            conn.rollback()
            print("↩ Transaction rolled back.")

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Connection closed.")


if __name__ == "__main__":
    main()
