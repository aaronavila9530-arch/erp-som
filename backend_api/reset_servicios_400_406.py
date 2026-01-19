import psycopg2
import sys

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()

        # --------------------------------------------------
        # 1. Verificación PREVIA
        # --------------------------------------------------
        print("\n🔎 Registros ANTES del cambio:")
        cur.execute("""
            SELECT consec, estado, num_informe
            FROM servicios
            WHERE consec BETWEEN 400 AND 406
            ORDER BY consec
        """)
        rows = cur.fetchall()

        if not rows:
            print("⚠️ No se encontraron registros en ese rango.")
            conn.close()
            return

        for r in rows:
            print(f"  consec={r[0]} | estado={r[1]} | num_informe={r[2]}")

        # --------------------------------------------------
        # 2. Confirmación
        # --------------------------------------------------
        print("\n⚠️ Se limpiará num_informe y se cambiará estado a 'Buque por confirmar'")
        confirm = input("¿Deseas continuar? (SI/NO): ").strip().upper()

        if confirm != "SI":
            print("❌ Operación cancelada por el usuario.")
            conn.close()
            return

        # --------------------------------------------------
        # 3. UPDATE CONTROLADO
        # --------------------------------------------------
        print("\n🧹 Aplicando cambios...")
        cur.execute("""
            UPDATE servicios
            SET
                num_informe = NULL,
                estado = 'Buque por confirmar'
            WHERE consec BETWEEN 400 AND 406
        """)

        conn.commit()
        print("✅ Cambios aplicados correctamente.")

        # --------------------------------------------------
        # 4. Verificación POSTERIOR
        # --------------------------------------------------
        print("\n🔎 Registros DESPUÉS del cambio:")
        cur.execute("""
            SELECT consec, estado, num_informe
            FROM servicios
            WHERE consec BETWEEN 400 AND 406
            ORDER BY consec
        """)
        rows = cur.fetchall()

        for r in rows:
            print(f"  consec={r[0]} | estado={r[1]} | num_informe={r[2]}")

        cur.close()
        conn.close()
        print("\n🎉 Proceso finalizado sin errores.")

    except Exception as e:
        print("\n❌ ERROR:")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
