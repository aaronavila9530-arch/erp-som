import psycopg2
from psycopg2.extras import execute_batch


DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)


PERMISSIONS = [

    # =====================================================
    # MASTER — ACCESO TOTAL ABSOLUTO
    # =====================================================
    ("master", "*", "*", True),

    # =====================================================
    # ADMIN — GESTIÓN TOTAL DE INFORMES
    # =====================================================
    ("admin", "informes", "view", True),
    ("admin", "informes", "create", True),
    ("admin", "informes", "edit", True),
    ("admin", "informes", "submit", True),
    ("admin", "informes", "approve", True),
    ("admin", "informes", "generate", True),
    ("admin", "informes", "delete", True),
    ("admin", "informes", "audit", True),

    # =====================================================
    # USER — SURVEYOR OPERATIVO
    # =====================================================
    ("user", "informes", "view", True),
    ("user", "informes", "create", True),
    ("user", "informes", "edit", True),
    ("user", "informes", "submit", True),

    # restricciones
    ("user", "informes", "approve", False),
    ("user", "informes", "generate", False),
    ("user", "informes", "delete", False),
    ("user", "informes", "audit", False),

    # =====================================================
    # CONSULTOR — AUDITORÍA
    # =====================================================
    ("consultor", "informes", "view", True),
    ("consultor", "informes", "audit", True),
    ("consultor", "informes", "generate", True),

    ("consultor", "informes", "create", False),
    ("consultor", "informes", "edit", False),
    ("consultor", "informes", "submit", False),
    ("consultor", "informes", "approve", False),
    ("consultor", "informes", "delete", False),
]


def main():

    conn = None

    try:

        print("🔐 Conectando a PostgreSQL...")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("🔐 Normalizando permisos RBAC — INFORMES")

        records = []

        for role, module, action, allowed in PERMISSIONS:

            role_norm = role.strip().lower()
            module_norm = module.strip().lower()
            action_norm = action.strip().lower()

            records.append(
                (role_norm, module_norm, action_norm, allowed)
            )

        execute_batch(
            cur,
            """
            INSERT INTO rbac_permissions (role_code, module, action, allowed)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (role_code, module, action)
            DO UPDATE SET
                allowed = EXCLUDED.allowed,
                created_at = NOW()
            """,
            records
        )

        conn.commit()

        print("✅ Permisos RBAC INFORMES normalizados correctamente")
        print(f"📊 Permisos procesados: {len(records)}")

    except Exception as e:

        if conn:
            conn.rollback()

        print("❌ Error actualizando permisos RBAC")
        print(str(e))

    finally:

        if conn:
            conn.close()

        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()