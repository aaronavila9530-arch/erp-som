import psycopg2

DB_URL = "postgresql://postgres:IrPzbLzKJFQtUnMlBKcHLHcLIAqagHCT@tramway.proxy.rlwy.net:15258/railway"


# =========================================================
# CONEXIÓN
# =========================================================
def get_conn():
    return psycopg2.connect(DB_URL)


# =========================================================
# CREAR TABLA (FLAT 10 SURVEYORS)
# =========================================================
def create_table():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS servicio_surveyors_flat (

        id SERIAL PRIMARY KEY,

        -- LINK
        servicio_consec INTEGER NOT NULL,

        -- SNAPSHOT DEL SERVICIO
        num_informe TEXT,
        cliente TEXT,
        pais TEXT,
        puerto TEXT,
        operacion TEXT,

        -- SURVEYORS (1..10)
        surveyor_1 TEXT,
        honorario_1 NUMERIC(12,2),

        surveyor_2 TEXT,
        honorario_2 NUMERIC(12,2),

        surveyor_3 TEXT,
        honorario_3 NUMERIC(12,2),

        surveyor_4 TEXT,
        honorario_4 NUMERIC(12,2),

        surveyor_5 TEXT,
        honorario_5 NUMERIC(12,2),

        surveyor_6 TEXT,
        honorario_6 NUMERIC(12,2),

        surveyor_7 TEXT,
        honorario_7 NUMERIC(12,2),

        surveyor_8 TEXT,
        honorario_8 NUMERIC(12,2),

        surveyor_9 TEXT,
        honorario_9 NUMERIC(12,2),

        surveyor_10 TEXT,
        honorario_10 NUMERIC(12,2),

        total_honorarios NUMERIC(14,2) DEFAULT 0,
        cantidad_surveyors INTEGER DEFAULT 0,

        creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        CONSTRAINT fk_servicio_flat
        FOREIGN KEY (servicio_consec)
        REFERENCES servicios(consec)
        ON DELETE CASCADE
    );
    """)

    cur.execute("""
    CREATE UNIQUE INDEX IF NOT EXISTS idx_servicio_flat_unique
    ON servicio_surveyors_flat(servicio_consec);
    """)

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Tabla FLAT creada correctamente")


# =========================================================
# SAVE (INSERT OR UPDATE)
# =========================================================
def save_flat(consec, surveyors):

    conn = get_conn()
    cur = conn.cursor()

    # 1. traer metadata del servicio
    cur.execute("""
        SELECT num_informe, cliente, pais, puerto, operacion
        FROM servicios
        WHERE consec = %s
    """, (consec,))

    row = cur.fetchone()

    if not row:
        raise Exception(f"No existe servicio {consec}")

    num_informe, cliente, pais, puerto, operacion = row

    # 2. preparar estructura 10 slots
    slots = []
    total = 0

    for i in range(10):
        if i < len(surveyors):
            s = surveyors[i]
            nombre = s.get("surveyor_nombre")
            honorario = float(s.get("honorario") or 0)

            slots.append((nombre, honorario))
            total += honorario
        else:
            slots.append((None, None))

    cantidad = len(surveyors)

    # 3. UPSERT
    cur.execute("""
    INSERT INTO servicio_surveyors_flat (
        servicio_consec,
        num_informe,
        cliente,
        pais,
        puerto,
        operacion,

        surveyor_1, honorario_1,
        surveyor_2, honorario_2,
        surveyor_3, honorario_3,
        surveyor_4, honorario_4,
        surveyor_5, honorario_5,
        surveyor_6, honorario_6,
        surveyor_7, honorario_7,
        surveyor_8, honorario_8,
        surveyor_9, honorario_9,
        surveyor_10, honorario_10,

        total_honorarios,
        cantidad_surveyors
    )
    VALUES (
        %s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s
    )
    ON CONFLICT (servicio_consec)
    DO UPDATE SET

        num_informe = EXCLUDED.num_informe,
        cliente = EXCLUDED.cliente,
        pais = EXCLUDED.pais,
        puerto = EXCLUDED.puerto,
        operacion = EXCLUDED.operacion,

        surveyor_1 = EXCLUDED.surveyor_1,
        honorario_1 = EXCLUDED.honorario_1,

        surveyor_2 = EXCLUDED.surveyor_2,
        honorario_2 = EXCLUDED.honorario_2,

        surveyor_3 = EXCLUDED.surveyor_3,
        honorario_3 = EXCLUDED.honorario_3,

        surveyor_4 = EXCLUDED.surveyor_4,
        honorario_4 = EXCLUDED.honorario_4,

        surveyor_5 = EXCLUDED.surveyor_5,
        honorario_5 = EXCLUDED.honorario_5,

        surveyor_6 = EXCLUDED.surveyor_6,
        honorario_6 = EXCLUDED.honorario_6,

        surveyor_7 = EXCLUDED.surveyor_7,
        honorario_7 = EXCLUDED.honorario_7,

        surveyor_8 = EXCLUDED.surveyor_8,
        honorario_8 = EXCLUDED.honorario_8,

        surveyor_9 = EXCLUDED.surveyor_9,
        honorario_9 = EXCLUDED.honorario_9,

        surveyor_10 = EXCLUDED.surveyor_10,
        honorario_10 = EXCLUDED.honorario_10,

        total_honorarios = EXCLUDED.total_honorarios,
        cantidad_surveyors = EXCLUDED.cantidad_surveyors;
    """, (
        consec,
        num_informe,
        cliente,
        pais,
        puerto,
        operacion,

        *[item for pair in slots for item in pair],

        total,
        cantidad
    ))

    # 4. actualizar tabla servicios (resumen)
    if cantidad == 0:
        resumen = ""
    elif cantidad == 1:
        resumen = surveyors[0]["surveyor_nombre"]
    else:
        resumen = f"Varios ({cantidad})"

    cur.execute("""
        UPDATE servicios
        SET
            surveyor = %s,
            honorarios = %s
        WHERE consec = %s
    """, (resumen, total, consec))

    conn.commit()
    cur.close()
    conn.close()

    print(f"✅ FLAT guardado para servicio {consec}")


# =========================================================
# GET
# =========================================================
def get_flat(consec):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT *
        FROM servicio_surveyors_flat
        WHERE servicio_consec = %s
    """, (consec,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


# =========================================================
# TEST
# =========================================================
if __name__ == "__main__":

    create_table()

    test = [
        {"surveyor_nombre": "Pabel Peña", "honorario": 500},
        {"surveyor_nombre": "Juan Manuel", "honorario": 700},
        {"surveyor_nombre": "Javier Fernandez", "honorario": 300}
    ]

    save_flat(400, test)

    data = get_flat(400)
    print("\n📦 DATA:")
    print(data)