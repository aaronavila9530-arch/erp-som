from fastapi import Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user


def require_permission(module: str, action: str):
    """
    Middleware RBAC genérico.
    """

    def checker(
        user=Depends(get_current_user),
        conn=Depends(get_db)
    ):
        if not user:
            raise HTTPException(401, "Usuario no autenticado")

        rol = user.get("rol")
        if not rol:
            raise HTTPException(401, "Rol no disponible para RBAC")

        # 🔑 NORMALIZAR SIN PISAR VARIABLES EXTERNAS
        role_code = rol.strip().upper()
        module_code = module.strip().lower()
        action_code = action.strip()

        # =========================================
        # MASTER → ACCESO TOTAL
        # =========================================
        if role_code == "MASTER":
            return True

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND module = %s
              AND (action = %s OR action = '*')
            ORDER BY
              CASE WHEN action = %s THEN 1 ELSE 2 END
            LIMIT 1
        """, (
            role_code,
            module_code,
            action_code,
            action_code
        ))

        perm = cur.fetchone()

        if not perm or not perm["allowed"]:
            raise HTTPException(403, "Acceso denegado por RBAC")

        return True

    return checker
