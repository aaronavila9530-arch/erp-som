import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway?sslmode=require"


def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    # =========================================================
    # 1️⃣ GENERAL DRAFT SURVEY
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS general_draft_survey (

            id SERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),

            -- Vessel / Survey
            vessel_mv TEXT,
            survey_no TEXT,
            call_letters TEXT,
            vessel_previous_names TEXT,
            flag TEXT,
            registry TEXT,
            built_year TEXT,
            by TEXT,

            -- People / Parties
            master TEXT,
            initial_surveyors TEXT,
            chief_officer TEXT,
            final_surveyors TEXT,
            chief_engineer TEXT,
            survey_requested_by TEXT,
            witness_draughts TEXT,
            on_account_of TEXT,
            witness_sounding TEXT,
            attended_also_by TEXT,

            -- Locations
            init_ships_location TEXT,
            final_ships_location TEXT,

            -- Dimensions
            length_overall TEXT,
            length_between_pp TEXT,
            extreme_breadth TEXT,
            moulded_breadth TEXT,
            depth_overall_incl_keel_plate TEXT,
            moulded_depth TEXT,
            summer_draught TEXT,
            summer_freeboard TEXT,

            -- Constants / Displacement
            constant_declared TEXT,
            constant_calculated TEXT,
            light_displacement TEXT,
            light_shipweight_plan TEXT,
            summer_displacement TEXT,
            summer_deadweight TEXT,
            net_register_tons TEXT,
            gross_register_tons TEXT,

            -- Hydrostatic
            hydro_tables_issued TEXT,
            trim_tables_available BOOLEAN,
            hydrometer_no TEXT,

            -- Status
            status TEXT DEFAULT 'Draft'
        );
    """)

    # =========================================================
    # 2️⃣ DRAFT SURVEY (INITIAL + FINAL)
    # =========================================================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS draft_survey (

            id SERIAL PRIMARY KEY,
            general_id INTEGER REFERENCES general_draft_survey(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),

            -- =========================
            -- INITIAL SURVEY
            -- =========================
            init_date DATE,
            init_time_from TEXT,
            init_time_to TEXT,
            init_cargo TEXT,
            init_port_from TEXT,
            init_port_to TEXT,

            init_draft_fwd_port TEXT,
            init_draft_fwd_stb TEXT,
            init_draft_mid_port TEXT,
            init_draft_mid_stb TEXT,
            init_draft_aft_port TEXT,
            init_draft_aft_stb TEXT,

            init_sg TEXT,

            init_ballast TEXT,
            init_fresh_water TEXT,
            init_fuel_oil TEXT,
            init_diesel_oil TEXT,
            init_lub_oil TEXT,
            init_others TEXT,
            init_deductions TEXT,

            -- =========================
            -- FINAL SURVEY
            -- =========================
            final_date DATE,
            final_time_from TEXT,
            final_time_to TEXT,

            final_draft_fwd_port TEXT,
            final_draft_fwd_stb TEXT,
            final_draft_mid_port TEXT,
            final_draft_mid_stb TEXT,
            final_draft_aft_port TEXT,
            final_draft_aft_stb TEXT,

            final_sg TEXT,

            final_ballast TEXT,
            final_fresh_water TEXT,
            final_fuel_oil TEXT,
            final_diesel_oil TEXT,
            final_lub_oil TEXT,
            final_others TEXT,
            final_deductions TEXT,

            -- Status
            status TEXT DEFAULT 'Draft'
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tables general_draft_survey and draft_survey created successfully.")


if __name__ == "__main__":
    main()
