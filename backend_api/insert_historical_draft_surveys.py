import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor


DATABASE_URL = os.getenv("HISTORICAL_DATABASE_URL")


GENERAL_COLUMNS = {
    "vessel_mv": "TEXT",
    "survey_no": "TEXT",
    "call_letters": "TEXT",
    "vessel_previous_names": "TEXT",
    "flag": "TEXT",
    "registry": "TEXT",
    "built_year": "TEXT",
    "by": "TEXT",
    "master": "TEXT",
    "initial_surveyors": "TEXT",
    "chief_officer": "TEXT",
    "final_surveyors": "TEXT",
    "chief_engineer": "TEXT",
    "survey_requested_by": "TEXT",
    "witness_draughts": "TEXT",
    "on_account_of": "TEXT",
    "witness_sounding": "TEXT",
    "attended_also_by": "TEXT",
    "init_ships_location": "TEXT",
    "final_ships_location": "TEXT",
    "length_overall": "TEXT",
    "length_between_pp": "TEXT",
    "extreme_breadth": "TEXT",
    "moulded_breadth": "TEXT",
    "depth_overall_incl_keel_plate": "TEXT",
    "moulded_depth": "TEXT",
    "summer_draught": "TEXT",
    "summer_freeboard": "TEXT",
    "constant_declared": "TEXT",
    "constant_calculated": "TEXT",
    "light_displacement": "TEXT",
    "light_shipweight_plan": "TEXT",
    "summer_displacement": "TEXT",
    "summer_deadweight": "TEXT",
    "net_register_tons": "TEXT",
    "gross_register_tons": "TEXT",
    "hydro_tables_issued": "TEXT",
    "trim_tables_available": "TEXT",
    "hydrometer_no": "TEXT",
    "year": "INTEGER",
    "month": "INTEGER",
    "continent": "TEXT",
    "country": "TEXT",
    "port": "TEXT",
    "client": "TEXT",
    "draft_report_number": "TEXT",
    "status": "TEXT",
}


DRAFT_COLUMNS = {
    "general_id": "INTEGER",
    "draft_report_number": "TEXT",
    "status": "TEXT",
    "year": "INTEGER",
    "month": "INTEGER",
    "continent": "TEXT",
    "country": "TEXT",
    "port": "TEXT",
    "client": "TEXT",
    "vessel_mv": "TEXT",
    "cargo": "TEXT",
    "port_from": "TEXT",
    "port_to": "TEXT",
    "loading": "TEXT",
    "unloading": "TEXT",
    "msl_surveyor": "TEXT",
    "init_cargo": "TEXT",
    "final_cargo": "TEXT",
    "init_port_from": "TEXT",
    "init_port_to": "TEXT",
    "purpose": "TEXT",
    "goods": "TEXT",
    "holds": "TEXT",
    "draft_survey_figures": "TEXT",
    "bl_figures": "TEXT",
    "draft_difference": "TEXT",
    "draft_percentage": "TEXT",
    "shore_scale_figures": "TEXT",
    "shore_scale_bl": "TEXT",
    "shore_scale_difference": "TEXT",
    "shore_scale_percentage": "TEXT",
    "remarks": "TEXT",
}


WORD_COLUMNS = {
    "draft_survey_id": "INTEGER",
    "draft_report_number": "TEXT",
    "status": "TEXT",
    "year": "INTEGER",
    "month": "INTEGER",
    "continent": "TEXT",
    "country": "TEXT",
    "port": "TEXT",
    "client": "TEXT",
    "word_mt": "TEXT",
    "word_product": "TEXT",
    "word_vessel": "TEXT",
    "word_port": "TEXT",
    "word_country": "TEXT",
    "word_survey_requested_by": "TEXT",
    "word_on_behalf_of": "TEXT",
    "word_master": "TEXT",
    "word_chief_officer": "TEXT",
    "word_name": "TEXT",
    "word_port_registry": "TEXT",
    "word_grt": "TEXT",
    "word_nrt": "TEXT",
    "word_year": "TEXT",
    "word_imo": "TEXT",
    "word_metric_tons": "TEXT",
    "word_goods_product": "TEXT",
    "word_holds": "TEXT",
    "word_draft_figures": "TEXT",
    "word_bl_figures": "TEXT",
    "word_difference": "TEXT",
    "word_percentage": "TEXT",
    "word_shore_scale": "TEXT",
    "word_shore_bl": "TEXT",
    "word_shore_difference": "TEXT",
    "word_shore_percentage": "TEXT",
    "word_arrived_buoy_date": "DATE",
    "word_arrived_buoy_time": "TIME",
    "word_nor_tendered_date": "DATE",
    "word_nor_tendered_time": "TIME",
    "word_all_fast_date": "DATE",
    "word_all_fast_time": "TIME",
    "word_initial_draft_date": "DATE",
    "word_initial_draft_time": "TIME",
    "word_commenced_date": "DATE",
    "word_commenced_time": "TIME",
    "word_completed_date": "DATE",
    "word_completed_time": "TIME",
    "word_final_draft_date": "DATE",
    "word_final_draft_time": "TIME",
    "purpose": "TEXT",
    "goods": "TEXT",
    "remarks": "TEXT",
}


BALLAST_COLUMNS = {
    "draft_survey_id": "INTEGER",
    "draft_report_number": "TEXT",
    "status": "TEXT",
    "year": "INTEGER",
    "month": "INTEGER",
    "continent": "TEXT",
    "country": "TEXT",
    "port": "TEXT",
    "client": "TEXT",
}


REPORTS = [
    {
        "num": "2181-1505-2026",
        "consec": 432,
        "vessel": "MV ASTRO ANTARES",
        "client": "EL SURCO",
        "requested_by": "AGROPECUARIA EL SURCO S.A.",
        "date": "2026-05-15",
        "month": 5,
        "master": "KOVALYOV KOSTYANTYN",
        "chief_officer": "BURYNDIN ANDRIY",
        "flag": "MARSHALL ISLANDS",
        "registry": "MAJURO",
        "grt": "34,624",
        "nrt": "19,725",
        "built": "2017",
        "imo": "9767065",
        "mt": "50,985.40",
        "product": "Grains in bulk (Soybean Yellow Corn DDGS)",
        "holds": "1-2-3-4-5",
        "arrived": ("2026-05-12", "08:45"),
        "nor": ("2026-05-12", "08:45"),
        "all_fast": ("2026-05-15", "22:30"),
        "initial": ("2026-05-16", "00:25"),
        "commenced": ("2026-05-16", "01:35"),
        "completed": ("2026-05-20", "20:20"),
        "final": ("2026-05-20", "20:20"),
        "draft_figures": "51,023.48",
        "bl_figures": "50,985.40",
        "difference": "38.08",
        "percentage": "0.07",
        "shore": "51,107.24",
        "shore_diff": "121.84",
        "shore_pct": "0.24",
    },
    {
        "num": "2175-1704-2026",
        "consec": 428,
        "vessel": "MV PMS ENZIAN",
        "client": "EL SURCO",
        "requested_by": "AGROPECUARIA EL SURCO S.A.",
        "date": "2026-04-24",
        "month": 4,
        "master": "SYDOROV SERGIY",
        "chief_officer": "ROLIK DMYTRO",
        "flag": "MARSHALL ISLANDS",
        "registry": "MAJURO",
        "grt": "34,619",
        "nrt": "20,170",
        "built": "2015",
        "imo": "9711420",
        "mt": "50,877.71",
        "product": "Grains in bulk (Soybean Yellow Corn DDGS)",
        "holds": "1-2-3-4-5",
        "arrived": ("2026-04-19", "17:18"),
        "nor": ("2026-04-19", "17:18"),
        "all_fast": ("2026-04-24", "19:45"),
        "initial": ("2026-04-24", "21:05"),
        "commenced": ("2026-04-24", "23:30"),
        "completed": ("2026-04-28", "16:40"),
        "final": ("2026-04-28", "16:40"),
        "draft_figures": "50,854.42",
        "bl_figures": "50,877.71",
        "difference": "-23.29",
        "percentage": "-0.05",
        "shore": "50,901.47",
        "shore_diff": "23.76",
        "shore_pct": "0.05",
    },
    {
        "num": "2168-0704-2026",
        "consec": 426,
        "vessel": "MV GREAT 61",
        "client": "EL SURCO",
        "requested_by": "AGROPECUARIA EL SURCO S.A.",
        "date": "2026-04-07",
        "month": 4,
        "master": "MUSTAFA KETENCI",
        "chief_officer": "ALPER GULDU",
        "flag": "SINGAPORE",
        "registry": "SINGAPORE",
        "grt": "34,584",
        "nrt": "20,215",
        "built": "2015",
        "imo": "9731365",
        "mt": "49,968.47",
        "product": "Grains in bulk (Soybean Yellow Corn)",
        "holds": "1-2-3-4-5",
        "arrived": ("2026-03-31", "14:15"),
        "nor": ("2026-03-31", "14:15"),
        "all_fast": ("2026-04-07", "20:00"),
        "initial": ("2026-04-07", "21:15"),
        "commenced": ("2026-04-07", "23:10"),
        "completed": ("2026-04-11", "10:10"),
        "final": ("2026-04-11", "10:00"),
        "draft_figures": "49,921.46",
        "bl_figures": "49,968.47",
        "difference": "-47.01",
        "percentage": "-0.09",
        "shore": "49,984.75",
        "shore_diff": "16.28",
        "shore_pct": "0.03",
    },
    {
        "num": "2166-0604-2026",
        "consec": 439,
        "vessel": "MV PERTH I",
        "client": "PANDI COSTA RICA",
        "requested_by": "PANDI COSTA RICA S.A.",
        "date": "2026-04-06",
        "month": 4,
        "master": "RAMPAL SANJIV",
        "chief_officer": "BIBICIOIU CATALIN",
        "flag": "MALTA",
        "registry": "VALLETTA",
        "grt": "33,044",
        "nrt": "19,231",
        "built": "2010",
        "imo": "9583550",
        "mt": "22,960.80",
        "product": "Grains in bulk (YELLOW CORN - WHEAT)",
        "holds": "1-3-4-5",
        "arrived": ("2026-03-26", "17:06"),
        "nor": ("2026-03-26", "17:06"),
        "all_fast": ("2026-04-01", "14:30"),
        "initial": ("2026-04-01", "15:50"),
        "commenced": ("2026-04-01", "19:00"),
        "completed": ("2026-04-06", "23:20"),
        "final": ("2026-04-06", "23:20"),
        "draft_figures": "22,987.62",
        "bl_figures": "22,960.80",
        "difference": "26.82",
        "percentage": "0.12",
        "shore": "23,135.41",
        "shore_diff": "174.61",
        "shore_pct": "0.76",
    },
]


def ensure_table(cur, table, columns):
    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table} (
            id SERIAL PRIMARY KEY,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
        """
    )
    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS id SERIAL")
    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()")
    cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW()")
    cur.execute(
        """
        SELECT 1
        FROM information_schema.table_constraints
        WHERE table_schema = 'public'
          AND table_name = %s
          AND constraint_type = 'PRIMARY KEY'
        LIMIT 1
        """,
        (table,),
    )
    if not cur.fetchone():
        cur.execute(f"ALTER TABLE {table} ADD PRIMARY KEY (id)")
    for name, ddl in columns.items():
        quoted = f'"{name}"' if name == "by" else name
        cur.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {quoted} {ddl}")
    cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_draft_report_number ON {table}(draft_report_number)")


def insert_dict(cur, table, data, returning=False):
    columns = list(data.keys())
    cols_sql = ", ".join([f'"{c}"' if c == "by" else c for c in columns])
    vals_sql = ", ".join(["%s"] * len(columns))
    suffix = " RETURNING id" if returning else ""
    cur.execute(
        f"INSERT INTO {table} ({cols_sql}) VALUES ({vals_sql}){suffix}",
        [data[c] for c in columns],
    )
    if returning:
        row = cur.fetchone()
        return row["id"] if isinstance(row, dict) else row[0]
    return None


def main():
    result = []
    if not DATABASE_URL:
        raise RuntimeError("HISTORICAL_DATABASE_URL is required")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        conn.autocommit = False
        cur = conn.cursor(cursor_factory=RealDictCursor)

        ensure_table(cur, "general_draft_survey", GENERAL_COLUMNS)
        ensure_table(cur, "draft_survey", DRAFT_COLUMNS)
        ensure_table(cur, "draft_survey_word_report", WORD_COLUMNS)
        ensure_table(cur, "draft_survey_ballast", BALLAST_COLUMNS)

        for report in REPORTS:
            num = report["num"]
            cur.execute(
                "SELECT id FROM general_draft_survey WHERE draft_report_number = %s LIMIT 1",
                (num,),
            )
            existing_general = cur.fetchone()

            if existing_general:
                general_id = existing_general["id"]
                action = "existing"
            else:
                purpose = (
                    f"Draft survey of {report['mt']} mt {report['product']} aboard "
                    f"{report['vessel']} at Puerto Caldera, Costa Rica."
                )
                general_id = insert_dict(
                    cur,
                    "general_draft_survey",
                    {
                        "vessel_mv": report["vessel"],
                        "survey_no": num,
                        "flag": report["flag"],
                        "registry": report["registry"],
                        "built_year": report["built"],
                        "master": report["master"],
                        "chief_officer": report["chief_officer"],
                        "survey_requested_by": report["requested_by"],
                        "on_account_of": report["client"],
                        "init_ships_location": "Puerto Caldera, Costa Rica",
                        "final_ships_location": "Puerto Caldera, Costa Rica",
                        "net_register_tons": report["nrt"],
                        "gross_register_tons": report["grt"],
                        "year": 2026,
                        "month": report["month"],
                        "continent": "América",
                        "country": "Costa Rica",
                        "port": "Caldera",
                        "client": report["client"],
                        "draft_report_number": num,
                        "status": "Created",
                    },
                    returning=True,
                )
                action = "inserted"

            cur.execute("SELECT id FROM draft_survey WHERE draft_report_number = %s LIMIT 1", (num,))
            draft_row = cur.fetchone()
            if draft_row:
                draft_id = draft_row["id"]
            else:
                purpose = (
                    f"Draft survey of {report['mt']} mt {report['product']} aboard "
                    f"{report['vessel']} at Puerto Caldera, Costa Rica."
                )
                draft_id = insert_dict(
                    cur,
                    "draft_survey",
                    {
                        "general_id": general_id,
                        "draft_report_number": num,
                        "status": "Created",
                        "year": 2026,
                        "month": report["month"],
                        "continent": "América",
                        "country": "Costa Rica",
                        "port": "Caldera",
                        "client": report["client"],
                        "vessel_mv": report["vessel"],
                        "cargo": report["product"],
                        "port_from": "",
                        "port_to": "Puerto Caldera, Costa Rica",
                        "loading": "",
                        "unloading": "Puerto Caldera",
                        "msl_surveyor": "MSL Marine Surveyor",
                        "init_cargo": report["product"],
                        "final_cargo": report["product"],
                        "purpose": purpose,
                        "goods": report["product"],
                        "holds": report["holds"],
                        "draft_survey_figures": report["draft_figures"],
                        "bl_figures": report["bl_figures"],
                        "draft_difference": report["difference"],
                        "draft_percentage": report["percentage"],
                        "shore_scale_figures": report["shore"],
                        "shore_scale_bl": report["bl_figures"],
                        "shore_scale_difference": report["shore_diff"],
                        "shore_scale_percentage": report["shore_pct"],
                        "remarks": "Historical Draft Survey loaded from issued PDF.",
                    },
                    returning=True,
                )

            cur.execute("SELECT id FROM draft_survey_word_report WHERE draft_report_number = %s LIMIT 1", (num,))
            if not cur.fetchone():
                purpose = (
                    f"Draft survey of {report['mt']} mt {report['product']} aboard "
                    f"{report['vessel']} at Puerto Caldera, Costa Rica."
                )
                insert_dict(
                    cur,
                    "draft_survey_word_report",
                    {
                        "draft_survey_id": draft_id,
                        "draft_report_number": num,
                        "status": "Created",
                        "year": 2026,
                        "month": report["month"],
                        "continent": "América",
                        "country": "Costa Rica",
                        "port": "Caldera",
                        "client": report["client"],
                        "word_mt": report["mt"],
                        "word_product": report["product"],
                        "word_vessel": report["vessel"],
                        "word_port": "Puerto Caldera",
                        "word_country": "Costa Rica",
                        "word_survey_requested_by": report["requested_by"],
                        "word_on_behalf_of": report["client"],
                        "word_master": report["master"],
                        "word_chief_officer": report["chief_officer"],
                        "word_name": report["vessel"],
                        "word_port_registry": report["registry"],
                        "word_grt": report["grt"],
                        "word_nrt": report["nrt"],
                        "word_year": report["built"],
                        "word_imo": report["imo"],
                        "word_metric_tons": report["mt"],
                        "word_goods_product": report["product"],
                        "word_holds": report["holds"],
                        "word_draft_figures": report["draft_figures"],
                        "word_bl_figures": report["bl_figures"],
                        "word_difference": report["difference"],
                        "word_percentage": report["percentage"],
                        "word_shore_scale": report["shore"],
                        "word_shore_bl": report["bl_figures"],
                        "word_shore_difference": report["shore_diff"],
                        "word_shore_percentage": report["shore_pct"],
                        "word_arrived_buoy_date": report["arrived"][0],
                        "word_arrived_buoy_time": report["arrived"][1],
                        "word_nor_tendered_date": report["nor"][0],
                        "word_nor_tendered_time": report["nor"][1],
                        "word_all_fast_date": report["all_fast"][0],
                        "word_all_fast_time": report["all_fast"][1],
                        "word_initial_draft_date": report["initial"][0],
                        "word_initial_draft_time": report["initial"][1],
                        "word_commenced_date": report["commenced"][0],
                        "word_commenced_time": report["commenced"][1],
                        "word_completed_date": report["completed"][0],
                        "word_completed_time": report["completed"][1],
                        "word_final_draft_date": report["final"][0],
                        "word_final_draft_time": report["final"][1],
                        "purpose": purpose,
                        "goods": report["product"],
                        "remarks": "Historical Draft Survey loaded from issued PDF.",
                    },
                )

            cur.execute("SELECT id FROM draft_survey_ballast WHERE draft_report_number = %s LIMIT 1", (num,))
            if not cur.fetchone():
                insert_dict(
                    cur,
                    "draft_survey_ballast",
                    {
                        "draft_survey_id": draft_id,
                        "draft_report_number": num,
                        "status": "Created",
                        "year": 2026,
                        "month": report["month"],
                        "continent": "América",
                        "country": "Costa Rica",
                        "port": "Caldera",
                        "client": report["client"],
                    },
                )

            cur.execute(
                """
                UPDATE servicios
                SET
                    cliente = %s,
                    buque_contenedor = %s,
                    pais = %s,
                    puerto = %s,
                    continente = %s,
                    operacion = %s,
                    status_informe = %s,
                    num_informe = %s
                WHERE consec = %s
                """,
                (
                    report["client"],
                    report["vessel"],
                    "Costa Rica",
                    "Caldera",
                    "América",
                    "DRAFT SURVEY",
                    "Created",
                    num,
                    report["consec"],
                ),
            )

            result.append({"num": num, "general_id": general_id, "draft_id": draft_id, "action": action})

        conn.commit()
        print(json.dumps({"ok": True, "reports": result}, ensure_ascii=False, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
