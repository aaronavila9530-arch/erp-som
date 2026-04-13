import sys
import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    conn = None

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False

        with conn.cursor() as cur:

            print("=== VALIDANDO ESTADO INICIAL ===")

            cur.execute("SELECT id, report_number FROM vessel_condition_surveys ORDER BY id;")
            rows = cur.fetchall()
            for r in rows:
                print(r)

            print("\n=== PASO 1: ELIMINAR ID 1 ===")
            cur.execute(
                "DELETE FROM vessel_condition_surveys WHERE id = %s",
                (1,)
            )
            print(f"Filas eliminadas: {cur.rowcount}")

            print("\n=== PASO 2: ACTUALIZAR ID 2 -> 1 ===")

            # ⚠️ Esto solo funciona si no hay conflicto con PK
            cur.execute(
                """
                UPDATE vessel_condition_surveys
                SET id = 1
                WHERE id = 2
                """
            )

            if cur.rowcount != 1:
                raise Exception("No se pudo actualizar id 2 → 1")

            print("OK: id 2 cambiado a 1")

            print("\n=== PASO 3: ACTUALIZAR REPORT NUMBER ===")

            cur.execute(
                """
                UPDATE vessel_condition_surveys
                SET report_number = %s
                WHERE id = %s
                """,
                ("2166-0604-2026", 1)
            )

            if cur.rowcount != 1:
                raise Exception("No se pudo actualizar report_number")

            print("OK: report_number actualizado")

            print("\n=== PASO 4: RESET SECUENCIA ===")

            # Detecta automáticamente la secuencia del SERIAL
            cur.execute(
                """
                SELECT pg_get_serial_sequence('vessel_condition_surveys', 'id')
                """
            )
            seq = cur.fetchone()[0]

            if not seq:
                raise Exception("No se pudo obtener la secuencia del ID")

            # Ajusta secuencia al máximo id actual
            cur.execute(
                f"""
                SELECT setval(%s, (SELECT MAX(id) FROM vessel_condition_surveys))
                """,
                (seq,)
            )

            print(f"OK: secuencia reseteada -> {seq}")

            conn.commit()

            print("\n=== RESULTADO FINAL ===")
            cur.execute("SELECT id, report_number FROM vessel_condition_surveys ORDER BY id;")
            rows = cur.fetchall()
            for r in rows:
                print(r)

            print("\n=== COMPLETADO ===")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()