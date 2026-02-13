import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

def run():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔄 Reestructurando tabla vessel_grain_sampling_reports...")

    # 1️⃣ Renombrar tabla original
    cur.execute("""
        ALTER TABLE vessel_grain_sampling_reports
        RENAME TO vessel_grain_sampling_reports_old;
    """)

    # 2️⃣ Crear nueva tabla alineada 1:1 con el Form
    cur.execute("""
        CREATE TABLE vessel_grain_sampling_reports (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),

            cert_no TEXT,
            place_date TEXT,

            requested_by TEXT,
            captain TEXT,
            chief_officer TEXT,
            vessel_name TEXT,

            -- SHIP DATA
            ship_flag TEXT,
            ship_grt TEXT,
            ship_nrt TEXT,
            ship_imo TEXT,
            ship_year TEXT,

            -- TIMES
            arrival_buoy_time TIMESTAMP,
            nor_tendered_time TIMESTAMP,
            holds_opening_time TIMESTAMP,
            surveyors_onboard_time TIMESTAMP,
            seals_verification_time TIMESTAMP,
            sampling_start_time TIMESTAMP,
            sampling_end_time TIMESTAMP,
            surveyors_disembark_time TIMESTAMP,

            -- PRODUCTS (5)
            hold1_product TEXT,
            hold1_tonnage TEXT,
            hold2_product TEXT,
            hold2_tonnage TEXT,
            hold3_product TEXT,
            hold3_tonnage TEXT,
            hold4_product TEXT,
            hold4_tonnage TEXT,
            hold5_product TEXT,
            hold5_tonnage TEXT,

            products_total TEXT,

            -- SAMPLING (3 BODEGAS × 5 PUNTOS)
            sample1_hold TEXT,
            sample1_proa_babor TEXT,
            sample1_proa_estribor TEXT,
            sample1_centro TEXT,
            sample1_popa_babor TEXT,
            sample1_popa_estribor TEXT,

            sample2_hold TEXT,
            sample2_proa_babor TEXT,
            sample2_proa_estribor TEXT,
            sample2_centro TEXT,
            sample2_popa_babor TEXT,
            sample2_popa_estribor TEXT,

            sample3_hold TEXT,
            sample3_proa_babor TEXT,
            sample3_proa_estribor TEXT,
            sample3_centro TEXT,
            sample3_popa_babor TEXT,
            sample3_popa_estribor TEXT,

            supervision TIMESTAMP,
            conclusion TEXT,

            -- STATUS SIEMPRE AL FINAL
            status TEXT
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla alineada 1:1 con el Form correctamente.")
    print("⚠️ La tabla anterior quedó como vessel_grain_sampling_reports_old.")

if __name__ == "__main__":
    run()
