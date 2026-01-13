import psycopg2

DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@shortline.proxy.rlwy.net:50018/railway"
)

PERMISSIONS = [

    # =====================================================
    # MASTER — ACCESO TOTAL
    # =====================================================
    ("MASTER", "hhrr", "*", True),

    # =====================================================
    # ADMIN / GERENCIA — OPERACIÓN COMPLETA
    # =====================================================
    ("ADMIN", "hhrr", "view", True),
    ("ADMIN", "hhrr", "create", True),
    ("ADMIN", "hhrr", "edit", True),
    ("ADMIN", "hhrr", "delete", True),

    # --- Payroll / RRHH ---
    ("ADMIN", "hhrr", "payroll", True),
    ("ADMIN", "hhrr", "employees", True),   # 🔑 CLAVE (FIX)
    ("ADMIN", "hhrr", "generate", True),
    ("ADMIN", "hhrr", "reports", True),

    # --- Registro de Horas ---
    ("ADMIN", "hhrr", "ot_log", True),
    ("ADMIN", "hhrr", "ot_log_view_all", True),
    ("ADMIN", "hhrr", "ot_log_status", True),
    ("ADMIN", "hhrr", "ot_log_export", True),

    # --- Aprobaciones ---
    ("ADMIN", "hhrr", "approve", True),

    ("ADMIN", "hhrr", "close_hr_module", False),

    # =====================================================
    # USER / EMPLOYEE — AUTOGESTIÓN
    # =====================================================
    ("USER", "hhrr", "view", True),
    ("USER", "hhrr", "create", True),
    ("USER", "hhrr", "edit", True),
    ("USER", "hhrr", "ot_log", True),

    ("USER", "hhrr", "ot_log_view_all", False),
    ("USER", "hhrr", "ot_log_status", False),
    ("USER", "hhrr", "ot_log_export", False),

    ("USER", "hhrr", "approve", False),
    ("USER", "hhrr", "payroll", False),
    ("USER", "hhrr", "employees", False),   # 🔒 explícito
    ("USER", "hhrr", "generate", False),
    ("USER", "hhrr", "reports", False),
    ("USER", "hhrr", "delete", False),
    ("USER", "hhrr", "close_hr_module", False),

    # =====================================================
    # CONSULTOR — LECTURA / AUDITORÍA
    # =====================================================
    ("CONSULTOR", "hhrr", "view", True),
    ("CONSULTOR", "hhrr", "payroll", True),
    ("CONSULTOR", "hhrr", "employees", True),  # 🔑 CLAVE (FIX)
    ("CONSULTOR", "hhrr", "reports", True),
    ("CONSULTOR", "hhrr", "generate", True),

    ("CONSULTOR", "hhrr", "ot_log", True),
    ("CONSULTOR", "hhrr", "ot_log_view_all", True),
    ("CONSULTOR", "hhrr", "ot_log_export", True),

    ("CONSULTOR", "hhrr", "create", False),
    ("CONSULTOR", "hhrr", "edit", False),
    ("CONSULTOR", "hhrr", "approve", False),
    ("CONSULTOR", "hhrr", "ot_log_status", False),
    ("CONSULTOR", "hhrr", "delete", False),
    ("CONSULTOR", "hhrr", "close_hr_module", False),
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Insertando permisos RBAC — HHRR")

    for role, module, action, allowed in PERMISSIONS:
        role_norm = str(role).strip().upper()
        module_norm = str(module).strip().lower()
        action_norm = str(action).strip()

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

    print("✅ Permisos HHRR insertados / actualizados correctamente.")


if __name__ == "__main__":
    main()
