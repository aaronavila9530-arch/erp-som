import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE_NAME = "vessel_bunker_reports"

# ==========================================
# COLUMNAS ESPERADAS (ALINEADAS A TU FORM)
# ==========================================
EXPECTED_COLUMNS = {
    # Header
    "bunker_cert_no", "ship_name", "port_of_registry", "gross_tonnage",
    "report_date", "certificate", "report_category", "client",
    "port", "country",

    # Delivery
    "dslop_date", "dslop_port", "dslop_country",
    "dslop_hour", "dslop_minute",

    # Antecedents
    "antecedent_arrived_port",
    "antecedent_arrived_dt",
    "antecedent_survey_date_from",
    "antecedent_survey_date_to",
    "antecedent_survey_hour_from",
    "antecedent_survey_minute_from",
    "antecedent_survey_hour_to",
    "antecedent_survey_minute_to",

    # Inspection
    "inspection_with",

    # Signatures
    "surveyor_name",
    "master_name",

    # Draft
    "draft_fwd", "draft_aft", "trim", "list",

    # Log Book Dates
    "log_eosp_date",
    "log_pob_date",
    "log_fwe_date",
    "log_bunker_date",
    "log_at_survey_date",

    # Log Book Hours
    "log_eosp_hour", "log_eosp_minute",
    "log_pob_hour", "log_pob_minute",
    "log_fwe_hour", "log_fwe_minute",
    "log_bunker_hour", "log_bunker_minute",
    "log_at_survey_hour", "log_at_survey_minute",

    # Log Book Fuel
    "log_eosp_vlsfo", "log_eosp_hfso", "log_eosp_mdo", "log_eosp_lsmgo",
    "log_pob_vlsfo", "log_pob_hfso", "log_pob_mdo", "log_pob_lsmgo",
    "log_fwe_vlsfo", "log_fwe_hfso", "log_fwe_mdo", "log_fwe_lsmgo",
    "log_at_survey_vlsfo", "log_at_survey_hfso",
    "log_at_survey_mdo", "log_at_survey_lsmgo",

    # Consumption
    "cons_sea_loaded_vlsfo", "cons_sea_loaded_hfso",
    "cons_sea_loaded_mdo", "cons_sea_loaded_lsmgo",
    "cons_sea_ballast_vlsfo", "cons_sea_ballast_hfso",
    "cons_sea_ballast_mdo", "cons_sea_ballast_lsmgo",
    "cons_port_ship_gear_vlsfo", "cons_port_ship_gear_hfso",
    "cons_port_ship_gear_mdo", "cons_port_ship_gear_lsmgo",
    "cons_port_shore_gear_vlsfo", "cons_port_shore_gear_hfso",
    "cons_port_shore_gear_mdo", "cons_port_shore_gear_lsmgo",
}


def main():
    print("Connecting to database...\n")

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
    """, (TABLE_NAME,))

    rows = cur.fetchall()
    db_columns = {r["column_name"] for r in rows}

    print("Total columns in DB:", len(db_columns))
    print("Expected frontend columns:", len(EXPECTED_COLUMNS))
    print()

    missing = EXPECTED_COLUMNS - db_columns
    extra = db_columns - EXPECTED_COLUMNS

    print("========================================")
    print("MISSING COLUMNS (Frontend expects them)")
    print("========================================")

    if not missing:
        print("✅ None — Schema fully aligned.")
    else:
        for col in sorted(missing):
            print("❌", col)

        print("\nSuggested SQL:")
        print("ALTER TABLE vessel_bunker_reports")
        print(",\n".join([f"ADD COLUMN {c} TEXT" for c in sorted(missing)]) + ";")

    print("\n========================================")
    print("UNUSED COLUMNS (In DB but not in form)")
    print("========================================")

    if not extra:
        print("✅ None.")
    else:
        for col in sorted(extra):
            print("⚠", col)

    cur.close()
    conn.close()

    print("\nAudit complete.")


if __name__ == "__main__":
    main()