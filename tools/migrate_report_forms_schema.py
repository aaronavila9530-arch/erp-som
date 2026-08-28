import os
import sys

import psycopg2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
BACKEND_DIR = os.path.join(ROOT, "backend_api")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from backend_api.database import DATABASE_URL  # noqa: E402


def common_columns():
    return [
        "report_number",
        "report_no",
        "certificate_no",
        "continent",
        "country",
        "port",
        "operation",
        "customer",
        "client",
        "requested_by",
        "vessel",
        "vessel_name",
        "date",
        "place",
        "location",
        "cargo",
        "commodity",
        "remarks",
        "conclusion",
        "link_picture",
        "status",
    ]


def port_captancy_columns():
    cols = [
        "report_number", "continent", "country", "port", "operation",
        "report_type", "vessel", "requested_by", "arrival_date",
        "arrival_hour", "arrival_minute", "inspection_date",
        "inspection_hour", "inspection_minute", "master", "chief",
        "flag", "grt", "nrt", "imo", "year_built", "link_picture",
    ]
    for i in range(5):
        cols.extend([f"ts_date_{i}", f"ts_hour_{i}", f"ts_min_{i}"])
    for i in range(1, 16):
        cols.append(f"operation_summary_{i}")
    for i in range(1, 16):
        cols.append(f"remarks_{i}")
    for i in range(1, 16):
        cols.append(f"conclusion_{i}")
    return cols


def vessel_cargo_condition_columns():
    cols = [
        "report_number", "continent", "operation", "service_start_date",
        "vessel", "port", "country", "requested_by", "master",
        "chief_officer", "vessel_port_registry_flag", "vessel_grt",
        "vessel_nrt", "vessel_imo_no", "vessel_year_build",
        "arrival_date", "arrival_hour", "arrival_minute",
        "inspection_date", "inspection_hour", "inspection_minute",
        "status", "sent_to_review_at", "link_picture", "cargo_type",
    ]
    for i in range(8):
        cols.extend([f"time_{i}_date", f"time_{i}_hour", f"time_{i}_minute"])
    for section in ("narrative", "findings", "remarks", "conclusion"):
        for n in range(1, 11):
            cols.append(f"{section}_{n}")
    return cols


def condition_survey_extra_columns():
    cols = ["vessel_name", "client", "customer"]
    for section in ("narrative", "survey_findings", "remarks", "conclusion"):
        for n in range(1, 21):
            cols.append(f"{section}_{n}")
    return cols


def hold_columns(prefixes):
    cols = []
    for i in range(1, 11):
        for prefix in prefixes:
            cols.append(f"hold_{i}_{prefix}")
    return cols


TABLES = {
    "port_captancy_reports": port_captancy_columns(),
    "vessel_cargo_condition_surveys": vessel_cargo_condition_columns(),
    "weight_certificates": [
        "report_number", "continent", "country", "port", "operation",
        "certificate_no",
        "vessel", "voyage", "commodity", "bl_figure", "cargo_hold",
        "shipper", "consignee", "terminal", "loading_port",
        "weight_determination", "date", "quantity", "remarks", "status",
    ],
    "vessel_holds_inspection_certificates": common_columns()
    + [
        "voyage", "bl_number", "holds_number", "vessel_holds_status",
        "master_chief_officer", "surveyor", "inspection_date",
        "completion_date", "place", "date", "load_port", "installation",
        "product", "inspection_time", "vessel_holds", "cargo_holds",
        "accepted_time", "place_location", "place_date", "hose_test_start",
        "hose_test_end",
    ]
    + hold_columns(("condition", "remarks")),
    "sampling_certificates": common_columns()
    + hold_columns(("seal", "sample", "remarks")),
    "sealing_certificates": common_columns()
    + ["chief_officer", "master", "surveyor", "closing_date", "closing_time"]
    + hold_columns(("fwd_escape", "fwd_aft_hatch", "aft_escape")),
    "lashing_certificates": [
        "report_no", "customer", "port", "country", "flat_rack_container",
        "cargo_type", "lashing_material", "place", "date",
        "ratchet_quantity", "where_carry_out", "completion_date", "status",
    ],
}


def unique(seq):
    seen = set()
    out = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


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
    for column in unique(columns):
        if column in {"id", "created_at", "updated_at"}:
            continue
        cur.execute(f'ALTER TABLE {table} ADD COLUMN IF NOT EXISTS "{column}" TEXT')


def main():
    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    try:
        with conn.cursor() as cur:
            for table, columns in TABLES.items():
                ensure_table(cur, table, columns)
            cur.execute('ALTER TABLE port_captancy_reports ADD COLUMN IF NOT EXISTS "status" TEXT')
            for column in condition_survey_extra_columns():
                cur.execute(f'ALTER TABLE vessel_condition_surveys ADD COLUMN IF NOT EXISTS "{column}" TEXT')
            cur.execute('ALTER TABLE vessel_bunker_reports ADD COLUMN IF NOT EXISTS "report_number" TEXT')
        conn.commit()
        print("Report form schema migration complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
