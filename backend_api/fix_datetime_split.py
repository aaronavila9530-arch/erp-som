import psycopg2
from datetime import datetime

# =========================================================
# 🔌 CONEXIÓN DB
# =========================================================
conn = psycopg2.connect(
    "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"
)

cur = conn.cursor()

# =========================================================
# 🧱 CAMPOS A PROCESAR
# =========================================================
datetime_fields = [
    "word_arrived_buoy",
    "word_nor_tendered",
    "word_all_fast",
    "word_initial_draft",
    "word_commenced",
    "word_completed",
    "word_final_draft"
]

# =========================================================
# 🛠️ 1. CREAR COLUMNAS NUEVAS
# =========================================================
for field in datetime_fields:
    date_col = f"{field}_date"
    time_col = f"{field}_time"

    try:
        cur.execute(f"""
            ALTER TABLE draft_survey_word_report
            ADD COLUMN IF NOT EXISTS {date_col} DATE;
        """)
        cur.execute(f"""
            ALTER TABLE draft_survey_word_report
            ADD COLUMN IF NOT EXISTS {time_col} TIME;
        """)
    except Exception as e:
        print(f"Error creando columnas para {field}: {e}")

conn.commit()

# =========================================================
# 🔍 2. LEER DATOS
# =========================================================
cur.execute(f"""
    SELECT id, {', '.join(datetime_fields)}
    FROM draft_survey_word_report
""")

rows = cur.fetchall()

# =========================================================
# 🔄 3. PROCESAR Y ACTUALIZAR
# =========================================================
for row in rows:
    record_id = row[0]

    updates = {}
    
    for i, field in enumerate(datetime_fields):
        raw_value = row[i + 1]

        if raw_value and isinstance(raw_value, str):
            try:
                # FORMATO ACTUAL: MM-DD-YYYYHH:MM
                dt = datetime.strptime(raw_value, "%m-%d-%Y%H:%M")

                updates[f"{field}_date"] = dt.date()
                updates[f"{field}_time"] = dt.time()

            except Exception:
                print(f"⚠️ No se pudo parsear: {field} -> {raw_value}")

    # =====================================================
    # 🧾 UPDATE DINÁMICO
    # =====================================================
    if updates:
        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values())

        cur.execute(f"""
            UPDATE draft_survey_word_report
            SET {set_clause}
            WHERE id = %s
        """, values + [record_id])

conn.commit()

# =========================================================
# 🧹 DONE
# =========================================================
cur.close()
conn.close()

print("✅ Migración completada: fechas y horas separadas correctamente.")