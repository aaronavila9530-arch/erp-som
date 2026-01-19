import psycopg2
from datetime import datetime

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

START_NUM = 2140  # primer informe válido


def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()

    print("🔌 Conectado a PostgreSQL")

    # --------------------------------------------------
    # 1. Obtener servicios FINALIZADOS con informe
    # --------------------------------------------------
    cur.execute("""
        SELECT consec, fecha_inicio
        FROM servicios
        WHERE estado = 'Finalizado'
          AND fecha_inicio IS NOT NULL
        ORDER BY fecha_inicio ASC, consec ASC
    """)
    rows = cur.fetchall()

    if not rows:
        print("❌ No hay servicios para procesar")
        conn.rollback()
        return

    print(f"🔎 Servicios a reconstruir: {len(rows)}")

    # --------------------------------------------------
    # 2. Reasignar num_informe SECUENCIAL
    # --------------------------------------------------
    current = START_NUM

    for consec, fecha_inicio in rows:
        fecha_dt = fecha_inicio if not isinstance(fecha_inicio, str) \
            else datetime.strptime(fecha_inicio[:10], "%Y-%m-%d")

        ddmm = fecha_dt.strftime("%d%m")
        year = fecha_dt.strftime("%Y")

        num_informe = f"{current}-{ddmm}-{year}"

        print(f"➡️ consec {consec} → {num_informe}")

        cur.execute("""
            UPDATE servicios
            SET num_informe = %s
            WHERE consec = %s
        """, (num_informe, consec))

        current += 1

    # --------------------------------------------------
    # 3. Resetear secuencia al último valor
    # --------------------------------------------------
    last_used = current - 1
    print(f"🔁 Alineando secuencia a {last_used}")

    cur.execute("""
        SELECT setval(
            'servicios_num_informe_seq',
            %s,
            true
        )
    """, (last_used,))

    conn.commit()
    conn.close()

    print("✅ Reconstrucción COMPLETA y consistente.")


if __name__ == "__main__":
    main()
