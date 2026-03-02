import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE_NAME = "vessel_cargo_condition_surveys"

CREATE_TABLE_SQL = f"""
CREATE TABLE {TABLE_NAME} (

    -- =========================================================
    -- CORE
    -- =========================================================
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

    -- =========================================================
    -- POPUP SELECTOR (PopupServicioDraftSelector -> _on_service_selected)
    -- values = (num_informe, buque, cliente, continente, pais, puerto, operacion, fecha_inicio)
    -- =========================================================
    report_number TEXT,          -- num_informe
    continent TEXT,              -- continente
    operation TEXT,              -- operacion
    service_start_date DATE,     -- fecha_inicio (si decides guardarlo)

    -- =========================================================
    -- 1. GENERAL INFORMATION (readonly fields in UI)
    -- =========================================================
    vessel TEXT,
    port TEXT,
    country TEXT,
    requested_by TEXT,
    master TEXT,
    chief_officer TEXT,

    -- =========================================================
    -- 1. GENERAL INFORMATION - DATETIME FIELDS
    -- UI keys:
    --   arrival_date, arrival_hour, arrival_minute
    --   inspection_date, inspection_hour, inspection_minute
    -- =========================================================
    arrival_date DATE,
    arrival_hour SMALLINT,
    arrival_minute SMALLINT,

    inspection_date DATE,
    inspection_hour SMALLINT,
    inspection_minute SMALLINT,

    -- =========================================================
    -- 3. EXTRACT TIME SHEET (8 eventos)
    -- UI keys: time_0_date/hour/minute ... time_7_date/hour/minute
    -- =========================================================
    time_0_date DATE,
    time_0_hour SMALLINT,
    time_0_minute SMALLINT,

    time_1_date DATE,
    time_1_hour SMALLINT,
    time_1_minute SMALLINT,

    time_2_date DATE,
    time_2_hour SMALLINT,
    time_2_minute SMALLINT,

    time_3_date DATE,
    time_3_hour SMALLINT,
    time_3_minute SMALLINT,

    time_4_date DATE,
    time_4_hour SMALLINT,
    time_4_minute SMALLINT,

    time_5_date DATE,
    time_5_hour SMALLINT,
    time_5_minute SMALLINT,

    time_6_date DATE,
    time_6_hour SMALLINT,
    time_6_minute SMALLINT,

    time_7_date DATE,
    time_7_hour SMALLINT,
    time_7_minute SMALLINT,

    -- =========================================================
    -- BULLET SECTIONS (10 bullet points por sección, 1 columna = 1 bullet)
    -- Narrative -> narrative_1..10
    -- Survey Findings -> findings_1..10
    -- Remarks -> remarks_1..10
    -- Conclusion -> conclusion_1..10
    -- =========================================================
    narrative_1 TEXT,
    narrative_2 TEXT,
    narrative_3 TEXT,
    narrative_4 TEXT,
    narrative_5 TEXT,
    narrative_6 TEXT,
    narrative_7 TEXT,
    narrative_8 TEXT,
    narrative_9 TEXT,
    narrative_10 TEXT,

    findings_1 TEXT,
    findings_2 TEXT,
    findings_3 TEXT,
    findings_4 TEXT,
    findings_5 TEXT,
    findings_6 TEXT,
    findings_7 TEXT,
    findings_8 TEXT,
    findings_9 TEXT,
    findings_10 TEXT,

    remarks_1 TEXT,
    remarks_2 TEXT,
    remarks_3 TEXT,
    remarks_4 TEXT,
    remarks_5 TEXT,
    remarks_6 TEXT,
    remarks_7 TEXT,
    remarks_8 TEXT,
    remarks_9 TEXT,
    remarks_10 TEXT,

    conclusion_1 TEXT,
    conclusion_2 TEXT,
    conclusion_3 TEXT,
    conclusion_4 TEXT,
    conclusion_5 TEXT,
    conclusion_6 TEXT,
    conclusion_7 TEXT,
    conclusion_8 TEXT,
    conclusion_9 TEXT,
    conclusion_10 TEXT,

    -- =========================================================
    -- WORKFLOW (opcional, pero útil en ERP)
    -- =========================================================
    status TEXT DEFAULT 'Draft',
    sent_to_review_at TIMESTAMP
);
"""

INDEXES_SQL = [
    f"CREATE INDEX idx_{TABLE_NAME}_created_at ON {TABLE_NAME}(created_at);",
    f"CREATE INDEX idx_{TABLE_NAME}_vessel ON {TABLE_NAME}(vessel);",
    f"CREATE INDEX idx_{TABLE_NAME}_port ON {TABLE_NAME}(port);",
    f"CREATE INDEX idx_{TABLE_NAME}_report_number ON {TABLE_NAME}(report_number);",
]


def main():
    conn = None
    cur = None
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        conn.autocommit = False
        cur = conn.cursor()

        print(f"Creating table: {TABLE_NAME}")
        cur.execute(CREATE_TABLE_SQL)

        for idx_sql in INDEXES_SQL:
            print(f"Creating index: {idx_sql}")
            cur.execute(idx_sql)

        conn.commit()
        print("✅ Table created successfully (1:1 aligned).")

    except Exception as e:
        print("❌ Error:", e)
        if conn:
            conn.rollback()
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()