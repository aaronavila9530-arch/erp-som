from fastapi import Header, HTTPException, Depends
from psycopg2.extras import RealDictCursor

from database import get_db


def get_current_user(
    x_user: str | None = Header(default=None, alias="X-User"),
    x_role: str | None = Header(default=None, alias="X-Role"),
    conn=Depends(get_db)
):
    """
    AUTH HHRR / ERP-SOM

    Lee usuario y rol desde headers:
    - X-User
    - X-Role

    Valida:
    - que existan
    - que el usuario exista en DB
    - que esté activo

    Retorna:
    {
        "usuario": "...",
        "nombre": "...",
        "rol": "..."
    }
    """

    # =====================================================
    # DEBUG REAL
    # =====================================================
    print(f"🔐 AUTH DEBUG | X-User={x_user!r} | X-Role={x_role!r}")

    # =====================================================
    # VALIDAR HEADERS
    # =====================================================
    if x_user is None or not str(x_user).strip():
        raise HTTPException(
            status_code=401,
            detail="Usuario no autenticado (X-User requerido)"
        )

    if x_role is None or not str(x_role).strip():
        raise HTTPException(
            status_code=401,
            detail="Rol no especificado (X-Role requerido)"
        )

    # =====================================================
    # NORMALIZAR
    # =====================================================
    usuario = str(x_user).strip().lower()
    rol = str(x_role).strip().lower()

    # =====================================================
    # VALIDAR USUARIO EN DB
    # =====================================================
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute(
            """
            SELECT
                usuario,
                nombre,
                activo
            FROM usuarios
            WHERE LOWER(TRIM(usuario)) = %s
            LIMIT 1
            """,
            (usuario,)
        )

        user = cur.fetchone()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando usuario: {str(e)}"
        )

    # =====================================================
    # USUARIO NO EXISTE
    # =====================================================
    if not user:
        raise HTTPException(
            status_code=401,
            detail=f"Usuario '{usuario}' no existe"
        )

    # =====================================================
    # USUARIO INACTIVO
    # =====================================================
    if not bool(user.get("activo")):
        raise HTTPException(
            status_code=403,
            detail=f"Usuario '{usuario}' inactivo"
        )

    # =====================================================
    # RESPUESTA FINAL
    # =====================================================
    return {
        "usuario": str(user["usuario"]).strip().lower(),
        "nombre": (user.get("nombre") or "").strip(),
        "rol": rol
    }