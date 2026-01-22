import psycopg2
from psycopg2.extras import RealDictCursor

# ============================================================
# DATABASE URL
# ============================================================
DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

# ============================================================
# CAMBIOS A APLICAR
# ============================================================
UPDATES = [
    (404, "Salina Cruz"),
    (400, "Chiapas"),
    (401, "Chiapas"),
]

# ============================================================
# MAIN
# ============================================================
def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    updated = 0
    skipped = 0

    for consec, nuevo_puerto in UPDATES:
        # Verificar existencia
        cur.execute("""
            SELECT puerto
            FROM servicios
            WHERE consec = %s
        """, (consec,))

        row = cur.fetchone()

        if not row:
            print(f"⏭️  consec {consec} no existe — omitido")
            skipped += 1
            continue

        cur.execute("""
            UPDATE servicios
            SET puerto = %s
            WHERE consec = %s
        """, (nuevo_puerto, consec))

        print(f"✅ consec {consec} → puerto actualizado a '{nuevo_puerto}'")
        updated += 1

    conn.commit()
    cur.close()
    conn.close()

    print("--------------------------------------------------")
    print(f"✔ Registros actualizados: {updated}")
    print(f"⏭️  Registros omitidos: {skipped}")
    print("✔ Proceso finalizado correctamente")

# ============================================================
# ENTRY POINT
# ============================================================
if __name__ == "__main__":
    main()
