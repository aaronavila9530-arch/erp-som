"""
RBAC — CLIENT SIDE (ERP-SOM)
⚠️ IMPORTANTE:
Este archivo NO consulta la base de datos.
El control REAL de permisos se hace en el BACKEND (FastAPI).

Aquí solo se usa para:
• Mostrar / ocultar opciones de UI
• Evitar crashes en cliente
• UX coherente

El backend seguirá devolviendo 401 / 403 si el usuario
intenta acceder a algo no permitido.
"""


def has_permission(role_code: str, module: str, action: str) -> bool:
    """
    Cliente Tkinter:
    Siempre devuelve True para evitar bloqueos por DB.

    La validación REAL se hace en el backend mediante:
    - require_permission
    - JWT
    - RBAC en FastAPI
    """

    # Normalizar
    role = (role_code or "").lower()
    module = (module or "").lower()
    action = (action or "").lower()

    # ==============================
    # CONTROL VISUAL BÁSICO (OPCIONAL)
    # ==============================
    # Puedes afinar esto si quieres ocultar botones por rol,
    # pero NUNCA conectarse a DB aquí.

    if role == "master":
        return True

    if role == "admin":
        return True

    if role == "consultor":
        # Consultor: solo lectura / revisión
        if action in ("view", "reports", "payroll", "generate"):
            return True
        return False

    if role == "user":
        # Empleado: autogestión
        if action in ("view", "create", "edit", "ot_log"):
            return True
        return False

    # Rol desconocido → bloquear UI
    return False
