import psycopg2
from psycopg2.extras import execute_batch


DATABASE_URL = (
    "postgresql://postgres:"
    "LjjyuIUsTSCdiwPVHSSwtIYPOsRQytGX"
    "@tramway.proxy.rlwy.net:15258/railway?sslmode=require"
)


PERMISSIONS = [

    # =====================================================
    # MASTER — ACCESO TOTAL GLOBAL
    # =====================================================
    ("master", "*", "*", True),

    # =====================================================
    # ADMIN — CONTROL COMPLETO HHRR
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
    ("admin", "hhrr", "payslips", True),

    # --- OT LOG ---
    ("admin", "hhrr", "ot_log", True),
    ("admin", "hhrr", "ot_log_view_all", True),
    ("admin", "hhrr", "ot_log_status", True),
    ("admin", "hhrr", "ot_log_export", True),
    ("admin", "hhrr", "hours_view", True),
    ("admin", "hhrr", "hours_register", True),
    ("admin", "hhrr", "hours_approve", True),
    ("admin", "hhrre", "hours_view", True),
    ("admin", "hhrre", "hours_register", True),
    ("admin", "hhrre", "hours_approve", True),
    ("admin", "hhrr", "salary_calculator", True),
    ("admin", "hhrr", "medical_network", True),

    # --- approvals ---
    ("admin", "hhrr", "approve", True),
    ("admin", "hhrr", "close_hr_module", False),

    # =====================================================
    # USER — AUTOGESTIÓN EMPLEADO
    # =====================================================
    ("user", "hhrr", "view", True),
    ("user", "hhrr", "create", True),
    ("user", "hhrr", "edit", True),

    # 🔥 OT LOG — FIX CRÍTICO (ESTO ERA EL PROBLEMA)
    ("user", "hhrr", "ot_log", True),          # summary + create + list
    ("user", "hhrr", "ot_log_view_all", False),
    ("user", "hhrr", "ot_log_status", False),
    ("user", "hhrr", "ot_log_export", False),
    ("user", "hhrr", "hours_view", True),
    ("user", "hhrr", "hours_register", True),
    ("user", "hhrr", "hours_approve", False),
    ("user", "hhrre", "hours_view", True),
    ("user", "hhrre", "hours_register", True),
    ("user", "hhrre", "hours_approve", False),
    ("user", "hhrr", "salary_calculator", False),
    ("user", "hhrr", "medical_network", True),

    # 🔥 AÑADIDOS PARA EVITAR 403 FUTUROS
    ("user", "hhrr", "me", True),              # endpoints tipo /me/*
    ("user", "hhrr", "summary", True),         # por si RBAC evalúa granular

    # --- PAYSLIPS ---
    ("user", "hhrr", "payslips", True),

    # --- BLOQUEOS ---
    ("user", "hhrr", "approve", False),
    ("user", "hhrr", "payroll", False),
    ("user", "hhrr", "employees", False),
    ("user", "hhrr", "generate", False),
    ("user", "hhrr", "reports", False),
    ("user", "hhrr", "delete", False),
    ("user", "hhrr", "close_hr_module", False),

    # =====================================================
    # CONSULTOR — LECTURA
    # =====================================================
    ("consultor", "hhrr", "view", True),
    ("consultor", "hhrr", "payroll", True),
    ("consultor", "hhrr", "employees", True),
    ("consultor", "hhrr", "reports", True),
    ("consultor", "hhrr", "generate", True),

    # --- OT LOG ---
    ("consultor", "hhrr", "ot_log", True),
    ("consultor", "hhrr", "ot_log_view_all", True),
    ("consultor", "hhrr", "ot_log_export", True),
    ("consultor", "hhrr", "hours_view", True),
    ("consultor", "hhrr", "hours_register", False),
    ("consultor", "hhrr", "hours_approve", False),
    ("consultor", "hhrre", "hours_view", True),
    ("consultor", "hhrre", "hours_register", False),
    ("consultor", "hhrre", "hours_approve", False),
    ("consultor", "hhrr", "salary_calculator", True),
    ("consultor", "hhrr", "medical_network", True),

    # --- PAYSLIPS ---
    ("consultor", "hhrr", "payslips", True),

    # --- BLOQUEOS ---
    ("consultor", "hhrr", "create", False),
    ("consultor", "hhrr", "edit", False),
    ("consultor", "hhrr", "approve", False),
    ("consultor", "hhrr", "ot_log_status", False),
    ("consultor", "hhrr", "delete", False),
    ("consultor", "hhrr", "close_hr_module", False),
]


def main():
    conn = None

    try:
        print("🔐 Conectando a PostgreSQL...")

        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        print("🔐 Aplicando permisos RBAC HHRR (ULTRA FIX)...")

        records = []

        for role, module, action, allowed in PERMISSIONS:
            records.append((
                role.strip().lower(),
                module.strip().lower(),
                action.strip().lower(),
                bool(allowed)
            ))

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

        print("✅ RBAC actualizado correctamente")
        print(f"📊 Total reglas: {len(records)}")

    except Exception as e:
        if conn:
            conn.rollback()

        print("❌ ERROR RBAC:")
        print(str(e))

    finally:
        if conn:
            conn.close()

        print("🔒 Conexión cerrada")


if __name__ == "__main__":
    main()
