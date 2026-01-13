import psycopg2

DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

PERMISSIONS = [

    # =====================================================
    # MASTER — ACCESO TOTAL REAL (GLOBAL)
    # =====================================================
    ("master", "*", "*", True),

    # =====================================================
    # ADMIN — OPERACIÓN COMPLETA HHRR
    # =====================================================
    ("admin", "hhrr", "view", True),
    ("admin", "hhrr", "create", True),
    ("admin", "hhrr", "edit", True),
    ("admin", "hhrr", "delete", True),

    # --- Payroll ---
    ("admin", "hhrr", "payroll", True),
    ("admin", "hhrr", "employees", True),
    ("admin", "hhrr", "generate", True),
    ("admin", "hhrr", "reports", True),

    # --- Registro de Horas ---
    ("admin", "hhrr", "ot_log", True),
    ("admin", "hhrr", "ot_log_view_all", True),
    ("admin", "hhrr", "ot_log_status", True),
    ("admin", "hhrr", "ot_log_export", True),

    # --- Aprobaciones ---
    ("admin", "hhrr", "approve", True),
    ("admin", "hhrr", "close_hr_module", False),

    # =====================================================
    # USER — AUTOGESTIÓN
    # =====================================================
    ("user", "hhrr", "view", True),
    ("user", "hhrr", "create", True),
    ("user", "hhrr", "edit", True),
    ("user", "hhrr", "ot_log", True),

    ("user", "hhrr", "ot_log_view_all", False),
    ("user", "hhrr", "ot_log_status", False),
    ("user", "hhrr", "ot_log_export", False),

    ("user", "hhrr", "approve", False),
    ("user", "hhrr", "payroll", False),
    ("user", "hhrr", "employees", False),
    ("user", "hhrr", "generate", False),
    ("user", "hhrr", "reports", False),
    ("user", "hhrr", "delete", False),
    ("user", "hhrr", "close_hr_module", False),

    # =====================================================
    # CONSULTOR — LECTURA / AUDITORÍA
    # =====================================================
    ("consultor", "hhrr", "view", True),
    ("consultor", "hhrr", "payroll", True),
    ("consultor", "hhrr", "employees", True),
    ("consultor", "hhrr", "reports", True),
    ("consultor", "hhrr", "generate", True),

    ("consultor", "hhrr", "ot_log", True),
    ("consultor", "hhrr", "ot_log_view_all", True),
    ("consultor", "hhrr", "ot_log_export", True),

    ("consultor", "hhrr", "create", False),
    ("consultor", "hhrr", "edit", False),
    ("consultor", "hhrr", "approve", False),
    ("consultor", "hhrr", "ot_log_status", False),
    ("consultor", "hhrr", "delete", False),
    ("consultor", "hhrr", "close_hr_module", False),
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Normalizando e insertando permisos RBAC — HHRR")

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

    print("✅ Permisos HHRR normalizados y actualizados correctamente.")


if __name__ == "__main__":
    main()
