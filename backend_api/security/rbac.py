from fastapi import Depends, HTTPException
from psycopg2.extras import RealDictCursor

from database import get_db
from security.auth import get_current_user


def require_permission(module: str, action: str):
    """
    Middleware RBAC genérico.
    Funciona para Servicios, Finanzas y HHRR.
    """

    def checker(
        user=Depends(get_current_user),
        conn=Depends(get_db)
    ):
        # -----------------------------------------
        # VALIDACIÓN DEFENSIVA (EVITA 500)
        # -----------------------------------------
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Usuario no autenticado"
            )

        rol = user.get("rol")
        if not rol:
            raise HTTPException(
                status_code=401,
                detail="Rol no disponible para RBAC"
            )

        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT allowed
            FROM rbac_permissions
            WHERE role_code = %s
              AND module = %s
              AND (action = %s OR action = '*')
            ORDER BY action DESC
            LIMIT 1
        """, (
            rol,       # ← YA VALIDADO
            module,
            action
        ))

        perm = cur.fetchone()

        if not perm or not perm["allowed"]:
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado por RBAC"
            )

        return True

    return checker
