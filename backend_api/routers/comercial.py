from fastapi import (
    APIRouter,
    Query,
    Header,
    HTTPException,
    Depends
)
from typing import Optional, List
from psycopg2.extras import RealDictCursor

from database import get_db
from rbac_service import has_permission


router = APIRouter(
    prefix="/comercial",
    tags=["Comercial"]
)

# ============================================================
# RBAC GUARD (MISMO PATRÓN QUE COLLECTIONS)
# ============================================================
def require_permission(module: str, action: str):
    def checker(
        x_user_role: str = Header(..., alias="X-User-Role")
    ):
        if not has_permission(x_user_role, module, action):
            raise HTTPException(
                status_code=403,
                detail="No autorizado"
            )
    return checker


# ============================================================
# GET /comercial/board
# PIZARRA COMERCIAL — SOLO LEE SERVICIOS
# ============================================================
@router.get(
    "/board",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_board(
    cliente: Optional[str] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    puerto: Optional[str] = Query(None),
    surveyor: Optional[str] = Query(None),
    estados: Optional[List[str]] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    """
    🔒 BLINDADO / ANTI-LAG:
    - Si NO hay filtros → retorna []
    - El frontend decide cuándo consultar
    - NO hay estados por defecto
    """

    # --------------------------------------------------------
    # Si no hay filtros → NO consultar DB
    # --------------------------------------------------------
    if not any([
        cliente,
        continente,
        pais,
        puerto,
        surveyor,
        estados,
        fecha_desde,
        fecha_hasta
    ]):
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    if cliente:
        filtros.append("cliente ILIKE %(cliente)s")
        params["cliente"] = f"%{cliente}%"

    if continente:
        filtros.append("continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("pais = %(pais)s")
        params["pais"] = pais

    if puerto:
        filtros.append("puerto = %(puerto)s")
        params["puerto"] = puerto

    if surveyor:
        filtros.append("surveyor ILIKE %(surveyor)s")
        params["surveyor"] = f"%{surveyor}%"

    if estados:
        filtros.append("estado = ANY(%(estados)s)")
        params["estados"] = estados

    if fecha_desde:
        filtros.append("fecha_inicio >= %(fecha_desde)s")
        params["fecha_desde"] = fecha_desde

    if fecha_hasta:
        filtros.append("fecha_inicio <= %(fecha_hasta)s")
        params["fecha_hasta"] = fecha_hasta

    where_sql = " AND ".join(filtros)

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
        WHERE {where_sql}
        ORDER BY fecha_inicio DESC
        LIMIT 500
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    return data
