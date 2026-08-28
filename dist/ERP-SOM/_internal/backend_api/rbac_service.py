"""RBAC ERP-SOM.

Mantiene reglas legacy por rol y, cuando se recibe username, consulta la tabla
user_module_permissions para permisos configurables desde el ERP.
"""


def _db_permission(username: str, module: str, action: str):
    if not username:
        return None
    try:
        from database import connect
        conn = connect()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT COUNT(*)
            FROM user_module_permissions
            WHERE lower(usuario)=lower(%s)
              AND allowed=TRUE
            """,
            (username,),
        )
        has_rows = (cur.fetchone() or [0])[0] > 0
        if not has_rows:
            decision = None
        else:
            cur.execute(
                """
                SELECT 1
                FROM user_module_permissions
                WHERE lower(usuario)=lower(%s)
                  AND lower(module_code)=lower(%s)
                  AND lower(action_code) IN (lower(%s), 'admin')
                  AND allowed=TRUE
                LIMIT 1
                """,
                (username, module, action),
            )
            decision = cur.fetchone() is not None
        cur.close()
        conn.close()
        return decision
    except Exception:
        return None


def has_permission(
    role_code: str,
    module: str,
    action: str,
    username: str | None = None
) -> bool:
    """
    Control visual RBAC cliente.

    Prioridad:

    1️⃣ Overrides por usuario
    2️⃣ Reglas por rol
    3️⃣ Fallback seguro
    """

    role = (role_code or "").lower()
    module = (module or "").lower()
    action = (action or "").lower()
    username = (username or "").lower()

    db_decision = _db_permission(username, module, action)
    if db_decision is not None:
        return db_decision

    # ======================================================
    # MASTER → TODO
    # ======================================================

    if role == "master":
        return True

    # ======================================================
    # OVERRIDES POR USUARIO (UI)
    # ======================================================

    USER_OVERRIDES = {

        # Surveyor
        "surveyor": {

            "comercial": ["view"],
            "hhrre": ["view"],
            "informes": ["view", "create", "edit", "submit"]

        },

        # Contabilidad
        "accountant": {

            "finanzas": ["view", "create", "edit"],
            "dashboard": ["view"]

        },

        "accounting01": {

            "finanzas": ["view", "create", "edit", "apply", "reverse", "sync", "generate", "reports"],
            "accounting": ["view", "create", "edit", "apply", "reverse", "sync", "generate", "reports"],
            "qa_som": ["view"]

        }

    }

    if username in USER_OVERRIDES:

        modules = USER_OVERRIDES[username]

        if module in modules:
            return action in modules[module]

        return False

    # ======================================================
    # REGLAS POR ROL
    # ======================================================

    ROLE_RULES = {

        "admin": {
            "*": ["*"]
        },

        # Perfil dedicado al equipo contable. Q&A solo requiere consulta;
        # Finanzas/Accounting conserva las acciones operativas del módulo.
        "accounting": {
            "finanzas": ["view", "create", "edit", "apply", "reverse", "sync", "generate", "reports"],
            "accounting": ["view", "create", "edit", "apply", "reverse", "sync", "generate", "reports"],
            "qa_som": ["view"]
        },

        "consultor": {
            "*": ["view", "reports", "generate"]
        },

        "user": {
            "*": ["view", "create", "edit", "ot_log"]
        }

    }

    if role in ROLE_RULES:

        rules = ROLE_RULES[role]

        # comodín módulo
        if "*" in rules:

            actions = rules["*"]

            if "*" in actions:
                return True

            return action in actions

        # módulo específico
        if module in rules:
            return action in rules[module]

    # ======================================================
    # FALLBACK SEGURO
    # ======================================================

    return False
