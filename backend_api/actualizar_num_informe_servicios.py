import sys
import psycopg2
from psycopg2.extras import RealDictCursor


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    updates = {
        433: "2163-2703-2026",
        428: "2165-0604-2026",
        434: "2166-0604-2026",
        437: "2167-0704-2026",
        426: "2168-0704-2026",
        427: "2169-0704-2026",
    }

    conn = None

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            print("=== VALIDANDO REGISTROS ===")

            for consec, nuevo_num_informe in updates.items():
                cur.execute(
                    """
                    SELECT consec, num_informe
                    FROM servicios
                    WHERE consec = %s
                    """,
                    (consec,)
                )
                row = cur.fetchone()

                if not row:
                    raise Exception(f"No existe ningún registro en servicios con consec = {consec}")

                print(
                    f"consec={row['consec']} | num_informe actual={row['num_informe']} "
                    f"-> nuevo={nuevo_num_informe}"
                )

            print("\n=== ACTUALIZANDO ===")

            total_actualizados = 0

            for consec, nuevo_num_informe in updates.items():
                cur.execute(
                    """
                    UPDATE servicios
                    SET num_informe = %s
                    WHERE consec = %s
                    """,
                    (nuevo_num_informe, consec)
                )

                if cur.rowcount != 1:
                    raise Exception(
                        f"Se esperaba actualizar 1 fila para consec={consec}, "
                        f"pero se actualizaron {cur.rowcount}"
                    )

                total_actualizados += cur.rowcount
                print(f"OK -> consec={consec} actualizado a num_informe={nuevo_num_informe}")

            conn.commit()

            print("\n=== COMPLETADO ===")
            print(f"Total de filas actualizadas: {total_actualizados}")

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