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
    ("master", "hhrre", "*", True),

    # =====================================================
    # ADMIN / GERENCIA — OPERACIÓN COMPLETA
    # =====================================================
    ("admin", "hhrre", "view", True),
    ("admin", "hhrre", "create", True),
    ("admin", "hhrre", "edit", True),
    ("admin", "hhrre", "approve", True),
    ("admin", "hhrre", "payroll", True),
    ("admin", "hhrre", "generate", True),
    ("admin", "hhrre", "reports", True),
    ("admin", "hhrre", "ot_log", True),
    ("admin", "hhrre", "delete", True),
    ("admin", "hhrre", "close_hr_module", False),

    # =====================================================
    # USER / EMPLOYEE — AUTOGESTIÓN
    # =====================================================
    ("user", "hhrre", "view", True),
    ("user", "hhrre", "create", True),      # solicitudes / OT
    ("user", "hhrre", "edit", True),        # antes de aprobar
    ("user", "hhrre", "ot_log", True),

    ("user", "hhrre", "approve", False),
    ("user", "hhrre", "payroll", False),
    ("user", "hhrre", "generate", False),
    ("user", "hhrre", "reports", False),
    ("user", "hhrre", "delete", False),
    ("user", "hhrre", "close_hr_module", False),

    # =====================================================
    # CONSULTOR — LECTURA + AUDITORÍA
    # =====================================================
    ("consultor", "hhrre", "view", True),
    ("consultor", "hhrre", "reports", True),
    ("consultor", "hhrre", "payroll", True),     # revisión
    ("consultor", "hhrre", "generate", True),    # colillas auditadas

    ("consultor", "hhrre", "create", False),
    ("consultor", "hhrre", "edit", False),
    ("consultor", "hhrre", "approve", False),
    ("consultor", "hhrre", "ot_log", False),
    ("consultor", "hhrre", "delete", False),
    ("consultor", "hhrre", "close_hr_module", False),
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
