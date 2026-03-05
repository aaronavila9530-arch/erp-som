import psycopg2


DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


def main():

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    sql = """
    CREATE TABLE IF NOT EXISTS vessel_crane_inspection_reports (

        id SERIAL PRIMARY KEY,

        -- =====================================================
        -- HEADER
        -- =====================================================
        report_number TEXT,
        vessel TEXT,
        grt TEXT,
        nrt TEXT,
        client TEXT,
        port TEXT,
        country TEXT,
        report_date DATE,

        -- =====================================================
        -- INTRODUCTION
        -- =====================================================
        intro_inspection_date DATE,
        intro_inspection_hour INTEGER,
        intro_inspection_minute INTEGER,
        intro_text TEXT,

        -- =====================================================
        -- CRANES GEAR SURVEY
        -- =====================================================
        gear_start_date DATE,
        gear_start_hour INTEGER,
        gear_start_minute INTEGER,

        gear_end_date DATE,
        gear_end_hour INTEGER,
        gear_end_minute INTEGER,

        gear_condition TEXT,
        gear_wires TEXT,
        gear_sheaves TEXT,
        gear_operability TEXT,

        -- =====================================================
        -- CRANE INSPECTION CHECKLIST (15 ITEMS)
        -- =====================================================
    """

    checklist_items = [
        "crane_access",
        "crane_machinery_space",
        "crane_operator_cabin",
        "crane_jib_head_sheaves",
        "hoisting_wire_end_pin",
        "luffing_wire_end_pin",
        "crane_wire_visual",
        "crane_housing_sheaves",
        "luffing_center_sheave",
        "cargo_block_sheave",
        "slack_hoisting_limit",
        "crane_jib_angle_limits",
        "crane_jib_angle_indicator",
        "crane_hoisting_limits",
        "pedestal_light_project"
    ]

    for item in checklist_items:
        sql += f"""
        {item}_done BOOLEAN,
        {item}_status TEXT,
        {item}_status1 TEXT,
        {item}_status2 TEXT,
        {item}_status3 TEXT,
        """

    sql += """
        -- =====================================================
        -- REMARKS BY CRANE (4 CRANES × 10 BULLETS)
        -- =====================================================
    """

    for crane in range(1, 5):
        for i in range(1, 11):
            sql += f"crane{crane}_remark_{i} TEXT,\n"

    sql += """
        -- =====================================================
        -- RECOMMENDATIONS (10)
        -- =====================================================
    """

    for i in range(1, 11):
        sql += f"recommendation_{i} TEXT,\n"

    sql += """
        -- =====================================================
        -- GRABS CONDITION SURVEY (10)
        -- =====================================================
    """

    for i in range(1, 11):
        sql += f"grabs_condition_{i} TEXT,\n"

    sql += """
        -- =====================================================
        -- CONCLUSION (20)
        -- =====================================================
    """

    for i in range(1, 21):
        sql += f"conclusion_{i} TEXT,\n"

    sql += """
        -- =====================================================
        -- ENCLOSURE
        -- =====================================================
        link_picture TEXT,

        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()

    );
    """

    cur.execute(sql)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ TABLE vessel_crane_inspection_reports CREATED SUCCESSFULLY")


if __name__ == "__main__":
    main()