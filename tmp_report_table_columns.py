import os

import psycopg2
from psycopg2.extras import RealDictCursor

DSN = os.getenv("DATABASE_URL") or (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@tramway.proxy.rlwy.net:15258/"
    "railway?sslmode=require"
)

tables = [
    "container_reports",
    "vessel_grain_sampling_reports",
    "vessel_truck_supervision_reports",
    "general_draft_survey",
    "draft_survey",
    "vessel_bunker_reports",
    "vessel_cargo_condition_surveys",
    "vessel_crane_inspection_reports",
    "vessel_condition_surveys",
    "port_captancy_reports",
    "weight_certificates",
    "vessel_holds_inspection_certificates",
    "sampling_certificates",
    "sealing_certificates",
    "lashing_certificates",
    "logra_reports",
]

conn = psycopg2.connect(DSN)
cur = conn.cursor(cursor_factory=RealDictCursor)
for table in tables:
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    rows = cur.fetchall()
    print("\nTABLE", table, "cols", len(rows))
    for row in rows:
        print(dict(row))
cur.close()
conn.close()
