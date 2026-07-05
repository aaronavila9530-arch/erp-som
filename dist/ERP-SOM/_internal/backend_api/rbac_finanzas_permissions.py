"""
RBAC — CLIENT SIDE (ERP-SOM)
Módulo: FINANZAS

⚠️ IMPORTANTE
Este archivo NO consulta PostgreSQL.

La seguridad REAL se valida en el backend mediante:
• require_permission
• RBAC en FastAPI
• autenticación

Aquí solo se usa para:

• Mostrar / ocultar botones
• Evitar crashes en cliente
• UX consistente
"""


def has_permission(
    role_code: str,
    module: str,
    action: str,
    username: str | None = None
) -> bool:

    role = (role_code or "").lower()
    module = (module or "").lower()
    action = (action or "").lower()
    username = (username or "").lower()

    # ======================================================
    # MASTER — ACCESO TOTAL
    # ======================================================

    if role == "master":
        return True

    # ======================================================
    # OVERRIDES POR USUARIO (UI)
    # ======================================================

    USER_OVERRIDES = {

        # Surveyor — sin acceso a finanzas
        "surveyor": {},

        # Contabilidad
        "accountant": {
            "finanzas": [
                "view",
                "create",
                "edit",
                "apply",
                "reverse",
                "sync",
                "generate",
                "reports",
            ]
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

            "finanzas": [
                "view",
                "create",
                "edit",
                "apply",
                "reverse",
                "sync",
                "generate",
                "reports"
            ]

        },

        "user": {

            "finanzas": [
                "view",
                "create",
                "edit",
                "apply",
                "reverse",
                "sync",
                "generate",
                "reports"
            ]

        },

        "consultor": {

            "finanzas": [
                "view",
                "create",
                "edit",
                "reverse",
                "generate",
                "reports"
            ]

        }

    }

    if role in ROLE_RULES:

        rules = ROLE_RULES[role]

        if module in rules:
            return action in rules[module]

    # ======================================================
    # BLOQUEOS EXPLÍCITOS
    # ======================================================

    if action in (
        "delete",
        "close_period",
        "close_financial_module"
    ):
        return False

    # ======================================================
    # FALLBACK SEGURO
    # ======================================================

    return False