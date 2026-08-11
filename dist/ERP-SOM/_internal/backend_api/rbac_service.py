"""
RBAC — CLIENT SIDE (ERP-SOM)

⚠️ IMPORTANTE
Este archivo NUNCA consulta la base de datos.

El control REAL de seguridad se hace en el BACKEND
mediante:

• require_permission
• RBAC
• autenticación

Este módulo SOLO controla:

• Mostrar / ocultar botones
• UX coherente
• Evitar crashes en cliente

Si el cliente intenta ejecutar algo indebido,
el backend devolverá 401 / 403.
"""


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
