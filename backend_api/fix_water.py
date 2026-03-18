# =========================================================
# ERP-SOM — FULL STRUCTURE UPGRADE (BALLAST + FW + TOTALS)
# =========================================================

import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

TABLE = "draft_survey_ballast"

def add_column(col, col_type):
    cur.execute(f"""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = '{TABLE}'
            AND column_name = '{col}'
        ) THEN
            ALTER TABLE {TABLE}
            ADD COLUMN {col} {col_type};
        END IF;
    END$$;
    """)
    print(f"✔ {col}")

print("🚀 AGREGANDO COLUMNAS FALTANTES...")

# =========================================================
# BALLAST (1–20 TANQUES P/S)
# =========================================================
for phase in ["init", "final"]:
    for i in range(1, 21):
        for side in ["p", "s"]:

            base = f"{phase}_wbt_{i}{side}"

            add_column(f"{base}_total", "FLOAT")
            add_column(f"{base}_name", "VARCHAR(100)")

# =========================================================
# FPT / APT / SLOP
# =========================================================
for phase in ["init", "final"]:
    for tank in ["fpt", "apt", "slop_tank"]:
        base = f"{phase}_{tank}"

        add_column(f"{base}_total", "FLOAT")
        add_column(f"{base}_name", "VARCHAR(100)")

# =========================================================
# FRESH WATER (1–20)
# =========================================================
for phase in ["init", "final"]:
    for i in range(1, 21):

        base = f"{phase}_fw_{i}"

        add_column(f"{base}_total", "FLOAT")
        add_column(f"{base}_name", "VARCHAR(100)")

# =========================================================
# TOTALES GENERALES
# =========================================================
add_column("init_total_ballast", "FLOAT")
add_column("final_total_ballast", "FLOAT")

add_column("init_total_fresh_water", "FLOAT")
add_column("final_total_fresh_water", "FLOAT")

print("✅ ESTRUCTURA COMPLETA LISTA")

cur.close()
conn.close()