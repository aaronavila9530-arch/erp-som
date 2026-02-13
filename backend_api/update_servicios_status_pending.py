import psycopg2

# ============================================
# ERP-SOM — UPDATE STATUS INFORME
# Cambia de 'Created' → 'Pending'
# En tabla: servicios
# Columna PK: consec
# ============================================

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

IDS_TO_UPDATE = [
    416, 401, 407, 405, 406, 402,
    409, 403, 400, 412, 404, 408, 414
]


def main():
    print("========================================")
    print(" ERP-SOM — STATUS UPDATE (SERVICIOS) ")
    print("========================================\n")

    conn = None

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # ========================================
        # UPDATE
        # ========================================
        cur.execute("""
            UPDATE servicios
            SET status_informe = 'Pending'
            WHERE consec = ANY(%s)
              AND status_informe = 'Created'
        """, (IDS_TO_UPDATE,))

        updated_rows = cur.rowcount
        conn.commit()

        print(f"✔ {updated_rows} registros actualizados correctamente.\n")

        print("========================================")
        print(" ✔ PROCESO FINALIZADO ")
        print("========================================")

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ ERROR:")
        print(str(e))

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
