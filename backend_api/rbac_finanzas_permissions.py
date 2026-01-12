"""
RBAC — CLIENT SIDE (ERP-SOM)
Módulo: FINANZAS

⚠️ IMPORTANTE:
Este archivo NO consulta PostgreSQL.
La validación REAL de permisos se hace en el BACKEND (FastAPI).

Aquí se usa SOLO para:
• Mostrar / ocultar opciones de UI
• Evitar errores de conexión
• UX consistente
"""


def has_permission(role_code: str, module: str, action: str) -> bool:
    """
    Control visual de permisos para FINANZAS (cliente Tkinter).

    El backend sigue siendo la autoridad final.
    """

    role = (role_code or "").lower()
    module = (module or "").lower()
    action = (action or "").lower()

    # ==============================
    # MASTER — TODO
    # ==============================
    if role == "master":
        return True

    # ==============================
    # ADMIN — OPERACIÓN COMPLETA
    # ==============================
    if role == "admin":
        if action in (
            "view",
            "create",
            "edit",
            "apply",
            "reverse",
            "sync",
            "generate",
            "reports",
        ):
            return True

        # Bloqueos explícitos
        if action in (
            "delete",
            "close_period",
            "close_financial_module",
        ):
            return False

        return False

    # ==============================
    # USER — OPERACIÓN NORMAL
    # ==============================
    if role == "user":
        if action in (
            "view",
            "create",
            "edit",
            "apply",
            "reverse",
            "sync",
            "generate",
            "reports",
        ):
            return True

        if action in (
            "delete",
            "close_period",
            "close_financial_module",
        ):
            return False

        return False

    # ==============================
    # CONSULTOR — CONTABLE / REPORTES
    # ==============================
    if role == "consultor":
        if action in (
            "view",
            "create",
            "edit",
            "reverse",
            "generate",
            "reports",
        ):
            return True

        return False

    # ==============================
    # ROL DESCONOCIDO
    # ==============================
    return False
