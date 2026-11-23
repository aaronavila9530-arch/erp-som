-- Run transactionally. Additive only: preserve every existing column and value.
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '20s';
ALTER TABLE vessel_bunker_reports
    ADD COLUMN IF NOT EXISTS antecedent_arrived_port TEXT,
    ADD COLUMN IF NOT EXISTS antecedent_survey_hour_from TEXT,
    ADD COLUMN IF NOT EXISTS antecedent_survey_hour_to TEXT,
    ADD COLUMN IF NOT EXISTS antecedent_survey_minute_from TEXT,
    ADD COLUMN IF NOT EXISTS antecedent_survey_minute_to TEXT,
    ADD COLUMN IF NOT EXISTS berthing_hour TEXT,
    ADD COLUMN IF NOT EXISTS berthing_minute TEXT,
    ADD COLUMN IF NOT EXISTS charterers_name TEXT,
    ADD COLUMN IF NOT EXISTS chief_engineer_name TEXT,
    ADD COLUMN IF NOT EXISTS dslop_hour TEXT,
    ADD COLUMN IF NOT EXISTS dslop_minute TEXT,
    ADD COLUMN IF NOT EXISTS owner_name TEXT,
    ADD COLUMN IF NOT EXISTS surveyor_name TEXT;
DO $$
DECLARE event TEXT; fuel TEXT;
BEGIN
    FOREACH event IN ARRAY ARRAY['log_eosp','log_pob','log_fwe','log_bunker','log_at_survey'] LOOP
        EXECUTE format('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS %I DATE',event||'_date');
        EXECUTE format('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS %I TEXT',event||'_hour');
        EXECUTE format('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS %I TEXT',event||'_minute');
        FOREACH fuel IN ARRAY ARRAY['vlsfo','hfso','mdo','lsmgo'] LOOP
            EXECUTE format('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS %I NUMERIC',event||'_'||fuel);
        END LOOP;
    END LOOP;
    FOREACH event IN ARRAY ARRAY['cons_sea_loaded','cons_sea_ballast','cons_port_ship_gear','cons_port_shore_gear'] LOOP
        FOREACH fuel IN ARRAY ARRAY['vlsfo','hfso','mdo','lsmgo'] LOOP
            EXECUTE format('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS %I NUMERIC',event||'_'||fuel);
        END LOOP;
    END LOOP;
END $$;
