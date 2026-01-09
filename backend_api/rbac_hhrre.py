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
    ("master", "hhrr", "*", True),

    # =====================================================
    # ADMIN / GERENCIA — OPERACIÓN COMPLETA
    # =====================================================
    ("admin", "hhrr", "view", True),
    ("admin", "hhrr", "create", True),
    ("admin", "hhrr", "edit", True),
    ("admin", "hhrr", "approve", True),
    ("admin", "hhrr", "payroll", True),
    ("admin", "hhrr", "generate", True),
    ("admin", "hhrr", "reports", True),
    ("admin", "hhrr", "ot_log", True),
    ("admin", "hhrr", "delete", True),
    ("admin", "hhrr", "close_hr_module", False),

    # =====================================================
    # USER / EMPLOYEE — AUTOGESTIÓN
    # =====================================================
    ("user", "hhrr", "view", True),
    ("user", "hhrr", "create", True),      # solicitudes / OT
    ("user", "hhrr", "edit", True),        # antes de aprobar
    ("user", "hhrr", "ot_log", True),

    ("user", "hhrr", "approve", False),
    ("user", "hhrr", "payroll", False),
    ("user", "hhrr", "generate", False),
    ("user", "hhrr", "reports", False),
    ("user", "hhrr", "delete", False),
    ("user", "hhrr", "close_hr_module", False),

    # =====================================================
    # CONSULTOR — LECTURA + AUDITORÍA
    # =====================================================
    ("consultor", "hhrr", "view", True),
    ("consultor", "hhrr", "reports", True),
    ("consultor", "hhrr", "payroll", True),     # revisión
    ("consultor", "hhrr", "generate", True),    # colillas auditadas

    ("consultor", "hhrr", "create", False),
    ("consultor", "hhrr", "edit", False),
    ("consultor", "hhrr", "approve", False),
    ("consultor", "hhrr", "ot_log", False),
    ("consultor", "hhrr", "delete", False),
    ("consultor", "hhrr", "close_hr_module", False),
]


def main():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    print("🔐 Insertando permisos RBAC — HHRR")

    for role, module, action, allowed in PERMISSIONS:
        cur.execute("""
            INSERT INTO rbac_permissions (role_code, module, action, allowed)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (role_code, module, action)
            DO UPDATE SET allowed = EXCLUDED.allowed
        """, (role, module, action, allowed))

    conn.commit()
    cur.close()
    conn.close()

    print("✅ Permisos HHRR insertados correctamente.")


if __name__ == "__main__":
    main()
