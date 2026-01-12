from fastapi import Header, HTTPException, Depends
from psycopg2.extras import RealDictCursor

from database import get_db


def get_current_user(
    x_user: str = Header(None, alias="X-User"),
    x_role: str = Header(None, alias="X-Role"),
    conn=Depends(get_db)
):
    """
    Obtiene el usuario autenticado desde headers:
    - X-User
    - X-Role
    y valida el usuario contra la tabla usuarios.
    """

    if not x_user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no autenticado (X-User requerido)"
        )

    if not x_role:
        raise HTTPException(
            status_code=401,
            detail="Rol no especificado (X-Role requerido)"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT usuario, nombre, activo
        FROM usuarios
        WHERE usuario = %s
        LIMIT 1
    """, (x_user,))

    user = cur.fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Usuario no existe"
        )

    if not user["activo"]:
        raise HTTPException(
            status_code=403,
            detail="Usuario inactivo"
        )

    # 🔑 CLAVE: agregar el rol para RBAC
    user["rol"] = x_role.upper()

    return user
