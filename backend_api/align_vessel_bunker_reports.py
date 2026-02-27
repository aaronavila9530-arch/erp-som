import sys
import psycopg2


# ============================================================
# ALIGN vessel_bunker_reports (DB -> FRONTEND 1:1)
# - Adds missing columns
# - Optionally drops extra columns (use --drop-extra)
# - Inspired by your inyectar_surveyors.py structure
# ============================================================

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

TABLE_NAME = "vessel_bunker_reports"
SCHEMA_NAME = "public"


# ============================================================
# FRONTEND "MANDATORY" COLUMN SET (1:1)
# NOTE: This list is derived from your actual table dump + frontend keys.
# If you add more UI vars later, add them here.
# ============================================================
DESIRED_COLUMNS = [
    # core
    "id",
    "bunker_cert_no",
    "ship_name",
    "port_of_registry",
    "gross_tonnage",
    "report_date",
    "certificate",
    "report_category",
    "client",
    "port",
    "country",
    "berthing_date",
    "commenced_date",
    "dslop_date",
    "dslop_port",
    "dslop_country",
    "bunker_delivery_declared",
    "rob_diff",
    "plus_consumption",
    "generator_until_aps",
    "cons_dept",
    "me_to_sea_buoy",
    "remarks",
    "draft",
    "draft_fwd",
    "draft_aft",
    "trim",
    "list",
    "status",
    "workflow_status",
    "created_at",
    "updated_at",

    # antecedents / inspection
    "antecedent_arrived_dt",
    "antecedent_survey_date_from",
    "antecedent_survey_date_to",
    "inspection_with",

    # engine log book (values)
    "log_eosp_vlsfo", "log_eosp_hfso", "log_eosp_mdo", "log_eosp_lsmgo",
    "log_pob_vlsfo", "log_pob_hfso", "log_pob_mdo", "log_pob_lsmgo",
    "log_fwe_vlsfo", "log_fwe_hfso", "log_fwe_mdo", "log_fwe_lsmgo",
    "log_at_survey_vlsfo", "log_at_survey_hfso", "log_at_survey_mdo", "log_at_survey_lsmgo",

    # consumption
    "cons_sea_loaded_vlsfo", "cons_sea_loaded_hfso", "cons_sea_loaded_mdo", "cons_sea_loaded_lsmgo",
    "cons_sea_ballast_vlsfo", "cons_sea_ballast_hfso", "cons_sea_ballast_mdo", "cons_sea_ballast_lsmgo",
    "cons_port_ship_gear_vlsfo", "cons_port_ship_gear_hfso", "cons_port_ship_gear_mdo", "cons_port_ship_gear_lsmgo",
    "cons_port_shore_gear_vlsfo", "cons_port_shore_gear_hfso", "cons_port_shore_gear_mdo", "cons_port_shore_gear_lsmgo",
]

# ============================================================
# Tanks (dynamic UI expects up to 20 per fuel)
# These exist in your table already (name/dist/gauge/volume_m3/temp_c/temp_f/density_15c/weight_mt)
# plus there are some legacy columns like vlsfo_tank_1_volume, etc.
# We align to the FRONTEND modern naming ( *_volume_m3, *_temp_c, etc.)
# ============================================================
for i in range(1, 21):
    for fuel in ("vlsfo", "mgo"):
        DESIRED_COLUMNS.extend([
            f"{fuel}_tank_{i}_name",
            f"{fuel}_tank_{i}_dist_mtrs",
            f"{fuel}_tank_{i}_gauge_mtrs",
            f"{fuel}_tank_{i}_volume_m3",
            f"{fuel}_tank_{i}_temp_c",
            f"{fuel}_tank_{i}_temp_f",
            f"{fuel}_tank_{i}_density_15c",
            f"{fuel}_tank_{i}_weight_mt",
        ])

# Totals (present in your schema dump)
DESIRED_COLUMNS.extend([
    "vlsfo_total",
    "hfso_total",
    "lsmgo_total",
    "mdo_total",
])

# Bunker figures (up to 10 in your table)
for i in range(1, 11):
    DESIRED_COLUMNS.extend([
        f"bunker_figure_{i}_name",
        f"bunker_figure_{i}_ifo",
        f"bunker_figure_{i}_vlsfo",
        f"bunker_figure_{i}_lsmgo",
    ])


# ============================================================
# Type rules (best-effort)
# If a column exists with another type, we do NOT change type here.
# ============================================================
TYPE_OVERRIDES = {
    "id": "BIGSERIAL PRIMARY KEY",
    "gross_tonnage": "NUMERIC",
    "draft": "NUMERIC",
    "draft_fwd": "NUMERIC",
    "draft_aft": "NUMERIC",
    "trim": "NUMERIC",
    "list": "NUMERIC",

    "report_date": "DATE",
    "berthing_date": "DATE",
    "commenced_date": "DATE",
    "dslop_date": "DATE",
    "antecedent_arrived_dt": "DATE",
    "antecedent_survey_date_from": "DATE",
    "antecedent_survey_date_to": "DATE",

    "created_at": "TIMESTAMP",
    "updated_at": "TIMESTAMP",

    "rob_diff": "NUMERIC",
    "plus_consumption": "NUMERIC",
    "bunker_delivery_declared": "NUMERIC",
    "generator_until_aps": "NUMERIC",
    "cons_dept": "NUMERIC",
    "me_to_sea_buoy": "NUMERIC",

    "vlsfo_total": "NUMERIC",
    "hfso_total": "NUMERIC",
    "lsmgo_total": "NUMERIC",
    "mdo_total": "NUMERIC",

    "workflow_status": "TEXT",
    "status": "TEXT",
}

# Tank numeric fields default to NUMERIC
for i in range(1, 21):
    for fuel in ("vlsfo", "mgo"):
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_dist_mtrs"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_gauge_mtrs"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_volume_m3"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_temp_c"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_temp_f"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_density_15c"] = "NUMERIC"
        TYPE_OVERRIDES[f"{fuel}_tank_{i}_weight_mt"] = "NUMERIC"

# Log & Consumption fields default numeric
def _is_numeric_metric(col: str) -> bool:
    prefixes = (
        "log_",
        "cons_",
        "bunker_figure_",
    )
    return col.startswith(prefixes)

# ============================================================
# CLI
# ============================================================
def _parse_args(argv):
    """
    Accepts:
      python align_vessel_bunker_reports.py
      python align_vessel_bunker_reports.py <POSTGRES_DSN>
      python align_vessel_bunker_reports.py <POSTGRES_DSN> --dry-run
      python align_vessel_bunker_reports.py <POSTGRES_DSN> --drop-extra
    """
    dsn = None
    dry_run = False
    drop_extra = False

    for a in argv[1:]:
        if a == "--dry-run":
            dry_run = True
        elif a == "--drop-extra":
            drop_extra = True
        elif a.startswith("postgresql://"):
            dsn = a

    if not dsn:
        dsn = DB_URL

    return dsn, dry_run, drop_extra


def _get_existing_columns(cur):
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
    """, (SCHEMA_NAME, TABLE_NAME))
    return [r[0] for r in cur.fetchall()]


def _col_type(col: str) -> str:
    if col in TYPE_OVERRIDES:
        return TYPE_OVERRIDES[col]

    if _is_numeric_metric(col):
        # bunker_figure_* numeric fields (except _name)
        if col.endswith("_name"):
            return "TEXT"
        return "NUMERIC"

    # defaults
    return "TEXT"


def main():
    dsn, dry_run, drop_extra = _parse_args(sys.argv)

    print("🔌 Conectando a PostgreSQL (Railway)...")
    print("   DSN:", dsn)
    print("   TABLE:", f"{SCHEMA_NAME}.{TABLE_NAME}")
    print("   dry_run:", dry_run)
    print("   drop_extra:", drop_extra)

    conn = psycopg2.connect(dsn)
    conn.autocommit = False

    try:
        cur = conn.cursor()

        print("🔎 Leyendo columnas existentes...")
        existing = _get_existing_columns(cur)
        existing_set = set(existing)

        desired_set = set(DESIRED_COLUMNS)

        missing = [c for c in DESIRED_COLUMNS if c not in existing_set]
        extra = [c for c in existing if c not in desired_set]

        print("📌 RESUMEN:")
        print("   - Existentes:", len(existing))
        print("   - Deseadas:", len(DESIRED_COLUMNS))
        print("   - Faltantes:", len(missing))
        print("   - Extras:", len(extra))

        # =====================================================
        # ADD missing columns
        # =====================================================
        if missing:
            print("\n➕ Columnas faltantes (se agregarán):")
            for c in missing:
                print("   -", c, "->", _col_type(c))

            if not dry_run:
                for c in missing:
                    col_sql_type = _col_type(c)

                    # Special case: id as BIGSERIAL PRIMARY KEY only if column truly missing.
                    # If table already has an id, it won't be here.
                    sql = f'ALTER TABLE "{SCHEMA_NAME}"."{TABLE_NAME}" ADD COLUMN "{c}" {col_sql_type};'
                    cur.execute(sql)

                conn.commit()
                print("✅ ADD COLUMN aplicado.")
            else:
                print("🧪 DRY-RUN: No se ejecutó ALTER TABLE (ADD).")
        else:
            print("\n✅ No faltan columnas.")

        # =====================================================
        # DROP extra columns (optional)
        # =====================================================
        if extra:
            print("\n🧹 Columnas extra en DB (no están en desired):")
            for c in extra:
                print("   -", c)

            if drop_extra:
                if not dry_run:
                    print("\n⚠️ DROP EXTRA ACTIVADO. Eliminando columnas extra...")
                    for c in extra:
                        # avoid dropping id always
                        if c == "id":
                            continue
                        sql = f'ALTER TABLE "{SCHEMA_NAME}"."{TABLE_NAME}" DROP COLUMN IF EXISTS "{c}";'
                        cur.execute(sql)

                    conn.commit()
                    print("✅ DROP COLUMN aplicado.")
                else:
                    print("🧪 DRY-RUN: No se ejecutó ALTER TABLE (DROP).")
            else:
                print("\nℹ️ drop_extra está OFF. No se borró nada.")
        else:
            print("\n✅ No hay columnas extra.")

        print("\n🎯 Listo. DB alineada a tu FRONTEND (ADD aplicado; DROP opcional).")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR durante el align:")
        print(e)

    finally:
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()