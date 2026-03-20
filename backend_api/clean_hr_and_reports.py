import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():
    print("🔌 Conectando a PostgreSQL...")

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("🚀 Iniciando limpieza controlada...\n")

        # =====================================================
        # 1️⃣ hr_events → eliminar id 3
        # =====================================================
        print("🧹 Eliminando hr_events id=3...")
        cur.execute("DELETE FROM hr_events WHERE id = 3;")

        # =====================================================
        # 2️⃣ TABLAS A LIMPIAR COMPLETAMENTE (RESET IDENTITY)
        # =====================================================
        tables_to_truncate = [
            "hr_ot_log",
            "lashing_certificates",
            "port_captancy_reports",
            "sampling_certificates",
            "sealing_certificates",
            "servicio_surveyors_flat",
            "vessel_bunker_reports",
            "vessel_cargo_condition_surveys",
            "vessel_condition_surveys",
            "vessel_crane_inspection_reports",
            "vessel_grain_sampling_reports",
            "vessel_holds_inspection_certificates",
            "weight_certificates",
            "vessel_grain_sampling_reports_old"
        ]

        for table in tables_to_truncate:
            print(f"🧹 TRUNCATE {table} ...")
            cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")

        # =====================================================
        # 3️⃣ CASO ESPECIAL: vessel_truck_supervision_reports
        # =====================================================
        print("\n🚛 Procesando vessel_truck_supervision_reports...")

        # eliminar id 1 y 2
        print("   ➤ Eliminando id 1 y 2...")
        cur.execute("""
            DELETE FROM vessel_truck_supervision_reports
            WHERE id IN (1, 2);
        """)

        # cambiar id 3 → 1
        print("   ➤ Reasignando id 3 → 1...")
        cur.execute("""
            UPDATE vessel_truck_supervision_reports
            SET id = 1
            WHERE id = 3;
        """)

        # resetear secuencia
        print("   ➤ Reseteando secuencia...")
        cur.execute("""
            SELECT setval(
                pg_get_serial_sequence('vessel_truck_supervision_reports', 'id'),
                COALESCE((SELECT MAX(id) FROM vessel_truck_supervision_reports), 1),
                true
            );
        """)

        # =====================================================
        # COMMIT FINAL
        # =====================================================
        conn.commit()
        print("\n✅ TODO COMPLETADO EXITOSAMENTE")

    except Exception as e:
        conn.rollback()
        print("\n❌ ERROR → ROLLBACK EJECUTADO")
        print(str(e))

    finally:
        cur.close()
        conn.close()
        print("\n🔒 Conexión cerrada")


if __name__ == "__main__":
    main()