from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor
from typing import Optional

from database import get_db
from security.auth import get_current_user


router = APIRouter(
    prefix="/hr/policies",
    tags=["HHRR - Policies"]
)


# =========================================================
# UTIL — RBAC
# =========================================================
def _check_admin_role(current_user):
    rol = (current_user.get("rol") or "").lower()
    if rol not in ("admin", "master"):
        raise HTTPException(status_code=403, detail="Acceso denegado")


# =========================================================
# HELPERS
# =========================================================
def _clean(v):
    if v in ("", None, "None"):
        return None
    return v


# =========================================================
# GET — LISTAR POLÍTICAS (PÚBLICO / EMPLEADOS)
# GET /hr/policies
# =========================================================
@router.get("")
def listar_politicas(
    categoria: Optional[str] = Query(None),
    solo_activas: bool = Query(True),
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    conditions = []
    params = {}

    if categoria:
        conditions.append("categoria = %(categoria)s")
        params["categoria"] = categoria

    if solo_activas:
        conditions.append("activo = true")

    where_sql = ""
    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    cur.execute(f"""
        SELECT
            id,
            categoria,
            titulo,
            contenido,
            articulo_ref,
            activo
        FROM hr_policies
        {where_sql}
        ORDER BY categoria, id
    """, params)

    data = cur.fetchall()
    cur.close()

    return {
        "total": len(data),
        "data": data
    }


# =========================================================
# POST — CREAR POLÍTICA (ADMIN / MASTER)
# POST /hr/policies
# =========================================================
@router.post("")
def crear_politica(
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    categoria = _clean(payload.get("categoria"))
    titulo = _clean(payload.get("titulo"))
    contenido = _clean(payload.get("contenido"))
    articulo_ref = _clean(payload.get("articulo_ref"))

    if not categoria or not titulo or not contenido:
        raise HTTPException(
            status_code=400,
            detail="categoria, titulo y contenido son obligatorios"
        )

    cur.execute("""
        INSERT INTO hr_policies (
            categoria,
            titulo,
            contenido,
            articulo_ref,
            creado_por
        )
        VALUES (
            %(categoria)s,
            %(titulo)s,
            %(contenido)s,
            %(articulo_ref)s,
            %(creado_por)s
        )
        RETURNING id
    """, {
        "categoria": categoria,
        "titulo": titulo,
        "contenido": contenido,
        "articulo_ref": articulo_ref,
        "creado_por": current_user.get("usuario")
    })

    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()

    return {
        "message": "Política creada correctamente",
        "id": new_id
    }


# =========================================================
# PUT — ACTUALIZAR POLÍTICA (ADMIN / MASTER)
# PUT /hr/policies/{policy_id}
# =========================================================
@router.put("/{policy_id}")
def actualizar_politica(
    policy_id: int,
    payload: dict,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    fields = []
    params = {"id": policy_id}

    for key in ("categoria", "titulo", "contenido", "articulo_ref", "activo"):
        if key in payload:
            fields.append(f"{key} = %({key})s")
            params[key] = payload.get(key)

    if not fields:
        raise HTTPException(
            status_code=400,
            detail="No hay campos para actualizar"
        )

    fields.append("actualizado_en = NOW()")

    cur.execute(f"""
        UPDATE hr_policies
        SET {", ".join(fields)}
        WHERE id = %(id)s
        RETURNING id
    """, params)

    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Política no encontrada"
        )

    conn.commit()
    cur.close()

    return {
        "message": "Política actualizada correctamente",
        "id": policy_id
    }


# =========================================================
# DELETE — ELIMINAR POLÍTICA (SOFT DELETE) (ADMIN / MASTER)
# DELETE /hr/policies/{policy_id}
# =========================================================
@router.delete("/{policy_id}")
def eliminar_politica(
    policy_id: int,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    _check_admin_role(current_user)

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        UPDATE hr_policies
        SET activo = false,
            actualizado_en = NOW()
        WHERE id = %(id)s
        RETURNING id
    """, {"id": policy_id})

    row = cur.fetchone()
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Política no encontrada"
        )

    conn.commit()
    cur.close()

    return {
        "message": "Política desactivada correctamente",
        "id": policy_id
    }
