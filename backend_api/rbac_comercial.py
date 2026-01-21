import psycopg2

DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

# =====================================================
# RBAC — MÓDULO COMERCIAL
# =====================================================
PERMISSIONS = [

    # =================================================
    # MASTER — ACCESO TOTAL
    # =================================================
    ("master", "*", "*", True),

    # =================================================
    # ADMIN — OPERACIÓN COMERCIAL COMPLETA
    # =================================================
    ("admin", "comercial", "view", True),
    ("admin", "comercial", "board", True),

    ("admin", "comercial", "clients", True),
    ("admin", "comercial", "ports", True),
    ("admin", "comercial", "services", True),
    ("admin", "comercial", "quotations", True),
    ("admin", "comercial", "contracts", True),
    ("admin", "comercial", "reports", True),

    ("admin", "comercial", "create", True),
    ("admin", "comercial", "edit", True),
    ("admin", "comercial", "delete", True),
    ("admin", "comercial", "export", True),

    # =================================================
    # USER — VISUALIZACIÓN / OPERACIÓN BÁSICA
    # =================================================
    ("user", "comercial", "view", True),
    ("user", "comercial", "board", True),

    ("user", "comercial", "clients", False),
    ("user", "comercial", "ports", False),
    ("user", "comercial", "services", False),
    ("user", "comercial", "quotations", False),
    ("user", "comercial", "contracts", False),
    ("user", "comercial", "reports", False),

    ("user", "comercial", "create", False),
    ("user", "comercial", "edit", False),
    ("user", "comercial", "delete", False),
    ("user", "comercial", "export", False),

    # =================================================
    # CONSULTOR — ANÁLISIS / EVOLUCIÓN COMERCIAL
    # =================================================
    ("consultor", "comercial", "view", True),
    ("consultor", "comercial", "board", True),

    ("consultor", "comercial", "clients", True),
    ("consultor", "comercial", "ports", True),
    ("consultor", "comercial", "services", True),
    ("consultor", "comercial", "reports", True),

    ("consultor", "comercial", "quotations", False),
    ("consultor", "comercial", "contracts", False),

    ("consultor", "comercial", "create", False),
    ("consultor", "comercial", "edit", False),
    ("consultor", "comercial", "delete", False),
    ("consultor", "comercial", "export", True),
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Normalizando e insertando permisos RBAC — COMERCIAL")

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

    print("✅ Permisos COMERCIAL normalizados y actualizados correctamente.")


if __name__ == "__main__":
    main()
