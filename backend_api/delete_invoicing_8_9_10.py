import psycopg2
import sys

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    conn = None
    try:
        print("🔌 Conectando a PostgreSQL...")
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = False
        cur = conn.cursor()

        # --------------------------------------------------
        # 1. Verificar registros ANTES (solo ID)
        # --------------------------------------------------
        print("\n🔎 Registros ANTES de eliminar en invoicing:")
        cur.execute("""
            SELECT id
            FROM invoicing
            WHERE id IN (8, 9, 10)
            ORDER BY id
        """)
        rows = cur.fetchall()

        if not rows:
            print("⚠️ No se encontraron registros con id 8, 9 o 10.")
            conn.rollback()
            return

        for r in rows:
            print(f"  id={r[0]}")

        # --------------------------------------------------
        # 2. Confirmación explícita
        # --------------------------------------------------
        confirm = input("\n⚠️ ¿Eliminar DEFINITIVAMENTE estas facturas? (SI/NO): ").strip().upper()
        if confirm != "SI":
            print("❌ Operación cancelada por el usuario.")
            conn.rollback()
            return

        # --------------------------------------------------
        # 3. DELETE CONTROLADO
        # --------------------------------------------------
        print("\n🗑️ Eliminando registros de invoicing...")
        cur.execute("""
            DELETE FROM invoicing
            WHERE id IN (8, 9, 10)
        """)

        print(f"✅ Filas eliminadas en invoicing: {cur.rowcount}")

        conn.commit()

        # --------------------------------------------------
        # 4. Verificación DESPUÉS
        # --------------------------------------------------
        print("\n🔎 Verificación DESPUÉS:")
        cur.execute("""
            SELECT id
            FROM invoicing
            WHERE id IN (8, 9, 10)
        """)
        rows = cur.fetchall()

        if not rows:
            print("✅ Facturas eliminadas correctamente.")
        else:
            print("⚠️ Aún existen registros:", rows)

        cur.close()
        conn.close()
        print("\n🎉 Proceso finalizado sin errores.")

    except Exception as e:
        if conn:
            conn.rollback()
        print("\n❌ ERROR:")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
