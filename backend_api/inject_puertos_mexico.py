import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE URL (PROVIDA)
# ============================================================
DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

# ============================================================
# DATA A INSERTAR
# ============================================================
REGISTROS = [
    ("América", "México", "Salina Cruz"),
    ("América", "México", "Chiapas")
]

# ============================================================
# MAIN
# ============================================================
def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    insertados = 0
    omitidos = 0

    for continente, pais, puerto in REGISTROS:
        cur.execute("""
            SELECT 1
            FROM continentes_paises_puertos
            WHERE continente = %s
              AND pais = %s
              AND puerto = %s
        """, (continente, pais, puerto))

        if cur.fetchone():
            print(f"⏭️  Ya existe: {continente} / {pais} / {puerto}")
            omitidos += 1
            continue

        cur.execute("""
            INSERT INTO continentes_paises_puertos (
                continente,
                pais,
                puerto
            )
            VALUES (%s, %s, %s)
        """, (continente, pais, puerto))

        print(f"✅ Insertado: {continente} / {pais} / {puerto}")
        insertados += 1

    conn.commit()
    cur.close()
    conn.close()

    print("--------------------------------------------------")
    print(f"✔ Insertados: {insertados}")
    print(f"⏭️  Omitidos (ya existían): {omitidos}")
    print("✔ Proceso finalizado correctamente")

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    main()
