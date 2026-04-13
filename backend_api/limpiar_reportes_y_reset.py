import sys
import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLES_TO_TRUNCATE = [
    "draft_survey",
    "draft_survey_ballast",
    "draft_survey_word_report",
    "general_draft_survey",
    "lashing_certificates",
    "port_captancy_reports",
    "sampling_certificates",
    "sealing_certificates",
    "vessel_bunker_reports",
    "vessel_cargo_condition_surveys",
    "vessel_crane_inspection_reports",
    "vessel_grain_sampling_reports",
    "vessel_holds_inspection_certificates",
    "weight_certificates",
]


def reset_sequence_for_table(cur, table_name, id_column="id"):
    cur.execute(
        "SELECT pg_get_serial_sequence(%s, %s)",
        (table_name, id_column)
    )
    seq = cur.fetchone()[0]

    if not seq:
        print(f"  - {table_name}: no tiene secuencia serial detectada en '{id_column}'")
        return

    cur.execute(
        f"SELECT COALESCE(MAX({id_column}), 1) FROM {table_name}"
    )
    max_id = cur.fetchone()[0]

    cur.execute(
        "SELECT setval(%s, %s, %s)",
        (seq, max_id, True)
    )

    print(f"  - {table_name}: secuencia reseteada a {max_id}")


def main():
    conn = None

    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False

        with conn.cursor() as cur:
            print("=== INICIO DE LIMPIEZA ===")

            # -------------------------------------------------
            # 1) VACÍAR TABLAS COMPLETAS
            # -------------------------------------------------
            print("\n=== TRUNCATE / DELETE DE TABLAS COMPLETAS ===")

            for table_name in TABLES_TO_TRUNCATE:
                print(f"\nProcesando tabla: {table_name}")

                # DELETE explícito para evitar sorpresas si hay FKs
                cur.execute(f"DELETE FROM {table_name}")
                print(f"  - filas eliminadas: {cur.rowcount}")

                reset_sequence_for_table(cur, table_name, "id")

            # -------------------------------------------------
            # 2) AJUSTE ESPECÍFICO EN vessel_truck_supervision_reports
            # -------------------------------------------------
            print("\n=== AJUSTE EN vessel_truck_supervision_reports ===")

            cur.execute(
                "SELECT id FROM vessel_truck_supervision_reports ORDER BY id"
            )
            before_rows = cur.fetchall()
            print(f"  - ids antes: {[r[0] for r in before_rows]}")

            # borrar id 1
            cur.execute(
                "DELETE FROM vessel_truck_supervision_reports WHERE id = %s",
                (1,)
            )
            print(f"  - eliminado id=1 -> filas: {cur.rowcount}")

            # borrar id 2
            cur.execute(
                "DELETE FROM vessel_truck_supervision_reports WHERE id = %s",
                (2,)
            )
            print(f"  - eliminado id=2 -> filas: {cur.rowcount}")

            # mover id 3 -> 1
            cur.execute(
                """
                UPDATE vessel_truck_supervision_reports
                SET id = %s
                WHERE id = %s
                """,
                (1, 3)
            )

            if cur.rowcount != 1:
                raise Exception(
                    "No se pudo cambiar id=3 a id=1 en vessel_truck_supervision_reports"
                )

            print("  - actualizado id=3 -> id=1")

            reset_sequence_for_table(cur, "vessel_truck_supervision_reports", "id")

            cur.execute(
                "SELECT id FROM vessel_truck_supervision_reports ORDER BY id"
            )
            after_rows = cur.fetchall()
            print(f"  - ids después: {[r[0] for r in after_rows]}")

            # -------------------------------------------------
            # COMMIT
            # -------------------------------------------------
            conn.commit()
            print("\n=== COMPLETADO CON ÉXITO ===")

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