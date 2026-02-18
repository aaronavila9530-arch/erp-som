import sys
import psycopg2


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


class CreateVesselTruckSupervisionTable:

    TABLE_NAME = "vessel_truck_supervision_reports"

    def run(self):
        conn = None
        cur = None

        try:
            conn = psycopg2.connect(DB_URL)
            cur = conn.cursor()

            # =========================================================
            # 1) Tabla principal (alineada 1:1 con el form)
            # =========================================================
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

                    -- ===== Header (Report Header) =====
                    cert_no TEXT,
                    port TEXT,
                    country TEXT,
                    report_date DATE,

                    -- ===== 2. BUQUE =====
                    vessel_name TEXT,
                    flag_port_registry TEXT,
                    grt TEXT,
                    nrt TEXT,
                    imo_no TEXT,
                    build_year TEXT,

                    -- ===== Representantes =====
                    captain TEXT,
                    chief_officer TEXT,

                    -- ===== Tiempos =====
                    arrival_date DATE,
                    inspection_date DATE,
                    supervision_completed_date DATE,

                    -- ===== 4. Proceso de Supervisión =====
                    process_text TEXT,

                    -- ===== 5. Hallazgos =====
                    findings_text TEXT,

                    -- ===== 6. Conclusión =====
                    conclusion_text TEXT
                );
            """)

            # =========================================================
            # 2) Trigger para updated_at automático
            # =========================================================
            cur.execute("""
                CREATE OR REPLACE FUNCTION set_updated_at()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

            cur.execute(f"""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1
                        FROM pg_trigger
                        WHERE tgname = '{self.TABLE_NAME}_set_updated_at'
                    ) THEN
                        CREATE TRIGGER {self.TABLE_NAME}_set_updated_at
                        BEFORE UPDATE ON {self.TABLE_NAME}
                        FOR EACH ROW
                        EXECUTE FUNCTION set_updated_at();
                    END IF;
                END $$;
            """)

            # =========================================================
            # 3) Índices útiles
            # =========================================================
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_cert_no
                ON {self.TABLE_NAME} (cert_no);
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_report_date
                ON {self.TABLE_NAME} (report_date);
            """)
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_{self.TABLE_NAME}_vessel_name
                ON {self.TABLE_NAME} (vessel_name);
            """)

            conn.commit()
            print(f"✅ OK: Tabla '{self.TABLE_NAME}' creada/verificada y trigger actualizado.")

        except Exception as e:
            if conn:
                conn.rollback()
            print("❌ ERROR creando tabla:")
            print(repr(e))
            sys.exit(1)

        finally:
            try:
                if cur:
                    cur.close()
            except Exception:
                pass
            try:
                if conn:
                    conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    CreateVesselTruckSupervisionTable().run()
