import psycopg2

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
    # ADMIN — GESTIÓN COMPLETA DE INFORMES
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
    # USER — REDACCIÓN OPERATIVA (SURVEYOR)
    # =====================================================
    ("user", "informes", "view", True),
    ("user", "informes", "create", True),
    ("user", "informes", "edit", True),
    ("user", "informes", "submit", True),

    ("user", "informes", "approve", False),
    ("user", "informes", "generate", False),
    ("user", "informes", "delete", False),
    ("user", "informes", "audit", False),

    # =====================================================
    # CONSULTOR — LECTURA / AUDITORÍA
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
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Normalizando e insertando permisos RBAC — INFORMES")

    for role, module, action, allowed in PERMISSIONS:
        role_norm = role.strip().lower()
        module_norm = module.strip().lower()
        action_norm = action.strip().lower()

        cur.execute(
            """
            INSERT INTO rbac_permissions (role_code, module, action, allowed)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (role_code, module, action)
            DO UPDATE SET allowed = EXCLUDED.allowed
            """,
            (role_norm, module_norm, action_norm, allowed)
        )

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Permisos INFORMES normalizados y actualizados correctamente.")


if __name__ == "__main__":
    main()
