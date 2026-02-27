import psycopg2

DATABASE_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

COLUMNS = [
    "antecedent_survey_hour_from",
    "antecedent_survey_hour_to",
    "antecedent_survey_minute_from",
    "antecedent_survey_minute_to",
    "dslop_hour",
    "dslop_minute",
    "log_at_survey_hour",
    "log_at_survey_minute",
    "log_bunker_hour",
    "log_bunker_minute",
    "log_eosp_hour",
    "log_eosp_minute",
    "log_fwe_hour",
    "log_fwe_minute",
    "log_pob_hour",
    "log_pob_minute",
]

def main():
    try:
        print("Connecting to DB...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        for col in COLUMNS:
            query = f"""
            ALTER TABLE vessel_bunker_reports
            ADD COLUMN IF NOT EXISTS {col} SMALLINT;
            """
            print(f"Adding column: {col}")
            cur.execute(query)

        conn.commit()
        print("✅ All missing hour/minute columns added successfully.")

    except Exception as e:
        print("❌ ERROR:", e)
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
        print("Connection closed.")

if __name__ == "__main__":
    main()