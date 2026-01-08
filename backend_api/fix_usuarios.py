import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://postgres:LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX@shortline.proxy.rlwy.net:50018/railway"


def main():
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor(cursor_factory=RealDictCursor)

        print("✅ Conectado a la base de datos")

        # =====================================================
        # 1️⃣ AGREGAR COLUMNAS nombre / apellido SI NO EXISTEN
        # =====================================================
        cur.execute("""
            ALTER TABLE usuarios
            ADD COLUMN IF NOT EXISTS nombre VARCHAR(100),
            ADD COLUMN IF NOT EXISTS apellido VARCHAR(100)
        """)
        print("✅ Columnas nombre / apellido verificadas")

        # =====================================================
        # 2️⃣ ACTUALIZAR EMAILS
        # =====================================================
        updates_email = [
            ("diana.quiros@mslogisticsgroup.com", "Gerencia1"),
            ("pabel.pena@mslogisticsgroup.com", "Captain"),
            ("administrativo@mslogisticsgroup.com", "aaron01"),
        ]

        for email, usuario in updates_email:
            cur.execute("""
                UPDATE usuarios
                SET email = %s
                WHERE usuario = %s
            """, (email, usuario))

        print("✅ Emails actualizados")

        # =====================================================
        # 3️⃣ ACTUALIZAR NOMBRE Y APELLIDO
        # =====================================================
        updates_nombre = [
            ("Diana", "Quiros", "Gerencia1"),
            ("Pabel", "Peña", "Captain"),
            ("Aaron", "Avila", "aaron01"),
            ("Administrador", "Total", "admin"),
        ]

        for nombre, apellido, usuario in updates_nombre:
            cur.execute("""
                UPDATE usuarios
                SET nombre = %s,
                    apellido = %s
                WHERE usuario = %s
            """, (nombre, apellido, usuario))

        print("✅ Nombre y apellido actualizados")

        conn.commit()
        print("🎉 CAMBIOS APLICADOS CORRECTAMENTE")

    except Exception as e:
        if conn:
            conn.rollback()
        print("❌ ERROR:", repr(e))

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()
