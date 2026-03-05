# ============================================================
# ALIGN TABLE 1:1 — vessel_crane_inspection_reports
# Run from CMD:
#    python align_crane_table.py
# ============================================================

import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


EXPECTED_COLUMNS = [

    "report_number","vessel","grt","nrt","client","port","country","report_date",

    "intro_inspection_date","intro_inspection_hour","intro_inspection_minute","intro_text",

    "gear_start_date","gear_start_hour","gear_start_minute",
    "gear_end_date","gear_end_hour","gear_end_minute",

    "gear_condition","gear_wires","gear_sheaves","gear_operability",

    "crane_access_done","crane_access_status","crane_access_status1","crane_access_status2","crane_access_status3",
    "crane_machinery_space_done","crane_machinery_space_status","crane_machinery_space_status1","crane_machinery_space_status2","crane_machinery_space_status3",
    "crane_operator_cabin_done","crane_operator_cabin_status","crane_operator_cabin_status1","crane_operator_cabin_status2","crane_operator_cabin_status3",
    "crane_jib_head_sheaves_done","crane_jib_head_sheaves_status","crane_jib_head_sheaves_status1","crane_jib_head_sheaves_status2","crane_jib_head_sheaves_status3",
    "hoisting_wire_end_pin_done","hoisting_wire_end_pin_status","hoisting_wire_end_pin_status1","hoisting_wire_end_pin_status2","hoisting_wire_end_pin_status3",
    "luffing_wire_end_pin_done","luffing_wire_end_pin_status","luffing_wire_end_pin_status1","luffing_wire_end_pin_status2","luffing_wire_end_pin_status3",
    "crane_wire_visual_done","crane_wire_visual_status","crane_wire_visual_status1","crane_wire_visual_status2","crane_wire_visual_status3",
    "crane_housing_sheaves_done","crane_housing_sheaves_status","crane_housing_sheaves_status1","crane_housing_sheaves_status2","crane_housing_sheaves_status3",
    "luffing_center_sheave_done","luffing_center_sheave_status","luffing_center_sheave_status1","luffing_center_sheave_status2","luffing_center_sheave_status3",
    "cargo_block_sheave_done","cargo_block_sheave_status","cargo_block_sheave_status1","cargo_block_sheave_status2","cargo_block_sheave_status3",
    "slack_hoisting_limit_done","slack_hoisting_limit_status","slack_hoisting_limit_status1","slack_hoisting_limit_status2","slack_hoisting_limit_status3",
    "crane_jib_angle_limits_done","crane_jib_angle_limits_status","crane_jib_angle_limits_status1","crane_jib_angle_limits_status2","crane_jib_angle_limits_status3",
    "crane_jib_angle_indicator_done","crane_jib_angle_indicator_status","crane_jib_angle_indicator_status1","crane_jib_angle_indicator_status2","crane_jib_angle_indicator_status3",
    "crane_hoisting_limits_done","crane_hoisting_limits_status","crane_hoisting_limits_status1","crane_hoisting_limits_status2","crane_hoisting_limits_status3",
    "pedestal_light_project_done","pedestal_light_project_status","pedestal_light_project_status1","pedestal_light_project_status2","pedestal_light_project_status3"
]


def add_remark_columns(cur):

    for crane in range(1, 5):
        for i in range(1, 11):
            col = f"crane{crane}_remark_{i}"
            cur.execute(f"""
            ALTER TABLE vessel_crane_inspection_reports
            ADD COLUMN IF NOT EXISTS {col} TEXT
            """)


def add_recommendation_columns(cur):

    for i in range(1, 11):
        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS recommendation_{i} TEXT
        """)


def add_grabs_columns(cur):

    for i in range(1, 11):
        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS grabs_condition_{i} TEXT
        """)


def add_conclusion_columns(cur):

    for i in range(1, 21):
        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS conclusion_{i} TEXT
        """)


def add_base_columns(cur):

    cur.execute("""
    ALTER TABLE vessel_crane_inspection_reports
    ADD COLUMN IF NOT EXISTS report_number TEXT,
    ADD COLUMN IF NOT EXISTS vessel TEXT,
    ADD COLUMN IF NOT EXISTS grt TEXT,
    ADD COLUMN IF NOT EXISTS nrt TEXT,
    ADD COLUMN IF NOT EXISTS client TEXT,
    ADD COLUMN IF NOT EXISTS port TEXT,
    ADD COLUMN IF NOT EXISTS country TEXT,
    ADD COLUMN IF NOT EXISTS report_date DATE,

    ADD COLUMN IF NOT EXISTS intro_inspection_date DATE,
    ADD COLUMN IF NOT EXISTS intro_inspection_hour TEXT,
    ADD COLUMN IF NOT EXISTS intro_inspection_minute TEXT,
    ADD COLUMN IF NOT EXISTS intro_text TEXT,

    ADD COLUMN IF NOT EXISTS gear_start_date DATE,
    ADD COLUMN IF NOT EXISTS gear_start_hour TEXT,
    ADD COLUMN IF NOT EXISTS gear_start_minute TEXT,

    ADD COLUMN IF NOT EXISTS gear_end_date DATE,
    ADD COLUMN IF NOT EXISTS gear_end_hour TEXT,
    ADD COLUMN IF NOT EXISTS gear_end_minute TEXT,

    ADD COLUMN IF NOT EXISTS gear_condition TEXT,
    ADD COLUMN IF NOT EXISTS gear_wires TEXT,
    ADD COLUMN IF NOT EXISTS gear_sheaves TEXT,
    ADD COLUMN IF NOT EXISTS gear_operability TEXT,

    ADD COLUMN IF NOT EXISTS link_picture TEXT,

    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP
    """)


def add_checklist_columns(cur):

    checklist = [
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

    for item in checklist:

        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS {item}_done BOOLEAN
        """)

        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS {item}_status TEXT
        """)

        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS {item}_status1 TEXT
        """)

        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS {item}_status2 TEXT
        """)

        cur.execute(f"""
        ALTER TABLE vessel_crane_inspection_reports
        ADD COLUMN IF NOT EXISTS {item}_status3 TEXT
        """)


def main():

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("Aligning vessel_crane_inspection_reports...")

    add_base_columns(cur)
    add_checklist_columns(cur)
    add_remark_columns(cur)
    add_recommendation_columns(cur)
    add_grabs_columns(cur)
    add_conclusion_columns(cur)

    conn.commit()

    print("TABLE SUCCESSFULLY ALIGNED 1:1")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()