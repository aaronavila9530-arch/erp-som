import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def build_dynamic_columns():

    sql = []

    sections = [
        "narrative",
        "survey_findings",
        "remarks",
        "conclusion"
    ]

    for section in sections:
        for i in range(1, 21):
            sql.append(f"{section}_{i} TEXT")

    return ",\n".join(sql)


def main():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    dynamic_columns = build_dynamic_columns()

    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS vessel_condition_surveys (

        id SERIAL PRIMARY KEY,

        -- =====================================================
        -- HEADER
        -- =====================================================

        report_number VARCHAR(120),
        continent VARCHAR(120),
        country VARCHAR(120),
        port VARCHAR(120),
        popup_operation VARCHAR(120),
        service_start_date DATE,

        -- =====================================================
        -- SECTION 1
        -- =====================================================

        report_type VARCHAR(200),
        requested_by VARCHAR(200),

        arrival_date DATE,
        arrival_hour VARCHAR(2),
        arrival_minute VARCHAR(2),

        inspection_date DATE,
        inspection_hour VARCHAR(2),
        inspection_minute VARCHAR(2),

        master_of_ship VARCHAR(200),
        chief_officer VARCHAR(200),

        -- =====================================================
        -- SECTION 2
        -- =====================================================

        vessel VARCHAR(200),
        port_registry_flag VARCHAR(200),
        grt VARCHAR(50),
        operation VARCHAR(50),
        nrt VARCHAR(50),
        imo_no VARCHAR(50),
        year_built VARCHAR(20),

        -- =====================================================
        -- SECTION 3 (TIME SHEET)
        -- =====================================================

        ts_1_date DATE,
        ts_1_hour VARCHAR(2),
        ts_1_minute VARCHAR(2),

        ts_2_date DATE,
        ts_2_hour VARCHAR(2),
        ts_2_minute VARCHAR(2),

        ts_3_date DATE,
        ts_3_hour VARCHAR(2),
        ts_3_minute VARCHAR(2),

        ts_4_date DATE,
        ts_4_hour VARCHAR(2),
        ts_4_minute VARCHAR(2),

        ts_5_date DATE,
        ts_5_hour VARCHAR(2),
        ts_5_minute VARCHAR(2),

        ts_6_date DATE,
        ts_6_hour VARCHAR(2),
        ts_6_minute VARCHAR(2),

        ts_7_date DATE,
        ts_7_hour VARCHAR(2),
        ts_7_minute VARCHAR(2),

        ts_8_date DATE,
        ts_8_hour VARCHAR(2),
        ts_8_minute VARCHAR(2),

        -- =====================================================
        -- SECTIONS 4 / 5 / 6 / 7
        -- =====================================================

        {dynamic_columns},

        -- =====================================================
        -- SECTION 8
        -- =====================================================

        link_picture TEXT,

        -- =====================================================
        -- SYSTEM
        -- =====================================================

        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),

        status VARCHAR(60)

    );
    """

    cur.execute(create_table_sql)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla vessel_condition_surveys creada correctamente.")


if __name__ == "__main__":
    main()