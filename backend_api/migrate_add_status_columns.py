import psycopg2
from psycopg2 import sql
from psycopg2.errors import DuplicateColumn


DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    print("========================================")
    print(" ERP-SOM — STATUS COLUMN MIGRATION ")
    print("========================================\n")

    conn = None

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # =========================================================
        # 1️⃣ TABLA SERVICIOS → status_informe
        # =========================================================
        print("▶ Verificando columna status_informe en tabla servicios...")

        try:
            cur.execute("""
                ALTER TABLE servicios
                ADD COLUMN status_informe TEXT
            """)
            print("✔ Columna status_informe creada.")

        except DuplicateColumn:
            print("⚠ La columna status_informe ya existe.")

        # =========================================================
        # ACTUALIZAR TODOS LOS REGISTROS A 'Created'
        # =========================================================
        print("▶ Actualizando TODOS los registros de servicios a 'Created'...")

        cur.execute("""
            UPDATE servicios
            SET status_informe = 'Created'
            WHERE status_informe IS NULL
        """)

        print(f"✔ {cur.rowcount} registros actualizados.")

        # =========================================================
        # 2️⃣ TABLA vessel_grain_sampling_reports → status
        # =========================================================
        print("\n▶ Verificando columna status en vessel_grain_sampling_reports...")

        try:
            cur.execute("""
                ALTER TABLE vessel_grain_sampling_reports
                ADD COLUMN status TEXT
            """)
            print("✔ Columna status creada.")

        except DuplicateColumn:
            print("⚠ La columna status ya existe.")

        # =========================================================
        # OPCIONAL: inicializar status en vessel
        # =========================================================
        print("▶ Inicializando status en vessel_grain_sampling_reports a 'Created'...")

        cur.execute("""
            UPDATE vessel_grain_sampling_reports
            SET status = 'Created'
            WHERE status IS NULL
        """)

        print(f"✔ {cur.rowcount} registros actualizados en vessel.")

        # =========================================================
        # COMMIT
        # =========================================================
        conn.commit()

        print("\n========================================")
        print(" ✔ MIGRACIÓN COMPLETADA EXITOSAMENTE ")
        print("========================================")

    except Exception as e:
        if conn:
            conn.rollback()
        print("\n❌ ERROR DURANTE MIGRACIÓN:")
        print(str(e))

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()
