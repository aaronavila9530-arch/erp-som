import psycopg2

# =========================================================
# CONEXION
# =========================================================
DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"

# =========================================================
# COLUMNAS QUE NO SE TOCAN
# =========================================================
EXCLUDE_COLUMNS = {
    "id",
    "draft_survey_id",
    "draftsurvey_id",
    "created_at",
    "updated_at"
}

# =========================================================
# MAIN
# =========================================================
def main():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    print("\n🔍 Leyendo columnas...")

    cur.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'draft_survey_ballast'
        ORDER BY ordinal_position
    """)

    columns = cur.fetchall()

    if not columns:
        print("❌ No se encontraron columnas")
        return

    to_alter = []

    for col_name, col_type in columns:

        if col_name in EXCLUDE_COLUMNS:
            continue

        # SOLO convertir si NO es texto ya
        if col_type not in ("text", "character varying"):
            to_alter.append(col_name)

    print(f"🧠 Columnas a convertir: {len(to_alter)}")

    # =========================================================
    # ALTER TABLE
    # =========================================================
    for col in to_alter:
        try:
            print(f"⚙️ Convirtiendo: {col}")

            cur.execute(f"""
                ALTER TABLE draft_survey_ballast
                ALTER COLUMN "{col}" TYPE TEXT
                USING "{col}"::TEXT
            """)

        except Exception as e:
            print(f"❌ Error en {col}: {e}")
            conn.rollback()
            continue

    conn.commit()

    print("\n✅ MIGRACIÓN COMPLETADA")
    print("🎯 Ahora la tabla acepta: EMPTY, GAUGE, números, TODO")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()