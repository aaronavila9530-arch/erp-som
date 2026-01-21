from fastapi import APIRouter, Depends, Query
from typing import Optional, List
from psycopg2.extras import RealDictCursor

from backend_api.database import get_db
from backend_api.auth import get_current_user
from backend_api.rbac_service import has_permission

router = APIRouter(
    prefix="/comercial",
    tags=["Comercial"]
)


# ============================================================
# BOARD — PIZARRA COMERCIAL
# ============================================================
@router.get("/board")
def comercial_board(
    cliente: Optional[str] = None,
    continente: Optional[str] = None,
    pais: Optional[str] = None,
    puerto: Optional[str] = None,
    surveyor: Optional[str] = None,
    estados: Optional[List[str]] = Query(None),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    """
    ⚠️ IMPORTANTE:
    - Si NO se envían filtros → devuelve [] (evita LAG)
    - Estados por defecto NO se aplican aquí
    """

    # --------------------------------------------------------
    # RBAC — SOLO VIEW
    # --------------------------------------------------------
    if not has_permission(current_user["rol"], "comercial", "view"):
        return []

    # --------------------------------------------------------
    # Si no hay filtros → NO CONSULTAR
    # --------------------------------------------------------
    if not any([cliente, continente, pais, puerto, surveyor, estados, fecha_desde, fecha_hasta]):
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    conditions = []
    params = {}

    if cliente:
        conditions.append("cliente ILIKE %(cliente)s")
        params["cliente"] = f"%{cliente}%"

    if continente:
        conditions.append("continente = %(continente)s")
        params["continente"] = continente

    if pais:
        conditions.append("pais = %(pais)s")
        params["pais"] = pais

    if puerto:
        conditions.append("puerto = %(puerto)s")
        params["puerto"] = puerto

    if surveyor:
        conditions.append("surveyor ILIKE %(surveyor)s")
        params["surveyor"] = f"%{surveyor}%"

    if estados:
        conditions.append("estado = ANY(%(estados)s)")
        params["estados"] = estados

    if fecha_desde:
        conditions.append("fecha_inicio >= %(fecha_desde)s")
        params["fecha_desde"] = fecha_desde

    if fecha_hasta:
        conditions.append("fecha_inicio <= %(fecha_hasta)s")
        params["fecha_hasta"] = fecha_hasta

    where_clause = " AND ".join(conditions)

    sql = f"""
        SELECT
            consec,
            tipo,
            estado,
            num_informe,
            buque_contenedor,
            cliente,
            detalle,
            continente,
            pais,
            puerto,
            operacion,
            surveyor,
            fecha_inicio,
            hora_inicio,
            fecha_fin,
            hora_fin,
            demoras,
            duracion
        FROM servicios
        WHERE {where_clause}
        ORDER BY fecha_inicio DESC
        LIMIT 500
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    return data
