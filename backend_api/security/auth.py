from fastapi import Header, HTTPException, Depends
from psycopg2.extras import RealDictCursor

from database import get_db


def get_current_user(
    x_user: str = Header(None, alias="X-User"),
    x_role: str = Header(None, alias="X-Role"),
    conn=Depends(get_db)
):
    """
    🔐 ERP-SOM — AUTH (ULTRA BLINDADO)

    Obtiene usuario desde headers:
    - X-User
    - X-Role

    ✔ Normaliza valores
    ✔ Valida existencia en DB
    ✔ Verifica activo
    ✔ Retorna estructura lista para RBAC

    ⚠️ CRÍTICO:
    Si el frontend NO envía headers → falla correctamente (401)
    """

    # =====================================================
    # 🔍 DEBUG (CLAVE PARA TU BUG ACTUAL)
    # =====================================================
    print("🔐 AUTH DEBUG → X-User:", x_user, "| X-Role:", x_role)

    # =====================================================
    # 🔒 VALIDACIÓN HEADERS
    # =====================================================
    if not x_user or not str(x_user).strip():
        raise HTTPException(
            status_code=401,
            detail="Usuario no autenticado (X-User requerido)"
        )

    if not x_role or not str(x_role).strip():
        raise HTTPException(
            status_code=401,
            detail="Rol no especificado (X-Role requerido)"
        )

    # =====================================================
    # 🧼 NORMALIZACIÓN
    # =====================================================
    usuario = str(x_user).strip().lower()
    rol = str(x_role).strip().lower()

    # =====================================================
    # 🔎 VALIDAR USUARIO EN DB
    # =====================================================
    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        cur.execute("""
            SELECT usuario, nombre, activo
            FROM usuarios
            WHERE LOWER(usuario) = %s
            LIMIT 1
        """, (usuario,))

        user = cur.fetchone()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validando usuario: {str(e)}"
        )

    # =====================================================
    # ❌ USUARIO NO EXISTE
    # =====================================================
    if not user:
        raise HTTPException(
            status_code=401,
            detail=f"Usuario '{usuario}' no existe"
        )

    # =====================================================
    # ❌ USUARIO INACTIVO
    # =====================================================
    if not user.get("activo"):
        raise HTTPException(
            status_code=403,
            detail=f"Usuario '{usuario}' inactivo"
        )

    # =====================================================
    # 🔐 ESTRUCTURA FINAL (RBAC READY)
    # =====================================================
    return {
        "usuario": user["usuario"].strip().lower(),
        "nombre": user.get("nombre"),
        "rol": rol  # 🔥 NORMALIZADO (lower)
    }