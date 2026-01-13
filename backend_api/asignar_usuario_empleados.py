import psycopg2

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"

ASIGNACIONES = {
    "MSL-0003-E": "admin",        # Aaron Avila
    "MSL-0002-E": "Gerencia1",    # Diana Quiros
    "MSL-0001-E": "Captain"       # Pabel Peña
}

def main():
    print("🔌 Conectando a PostgreSQL (Railway)...")
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    try:
        for codigo, usuario in ASIGNACIONES.items():
            print(f"➡️  Asignando usuario '{usuario}' a empleado {codigo}")

            cur.execute(
                """
                UPDATE empleados
                SET usuario = %s
                WHERE codigo = %s
                """,
                (usuario, codigo)
            )

            if cur.rowcount == 0:
                print(f"⚠️  No se encontró empleado con código {codigo}")
            else:
                print(f"✅ Actualizado {codigo}")

        conn.commit()
        print("\n🎉 Proceso completado correctamente.")

    except Exception as e:
        conn.rollback()
        print("❌ ERROR. Rollback ejecutado.")
        raise e

    finally:
        cur.close()
        conn.close()
        print("🔒 Conexión cerrada.")


if __name__ == "__main__":
    main()
