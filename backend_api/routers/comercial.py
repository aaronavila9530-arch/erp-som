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
        params["cliente"] = f"%{cliente.strip()}%"

    if continente:
        filtros.append("continente = %(continente)s")
        params["continente"] = continente.strip()

    if pais:
        filtros.append("pais = %(pais)s")
        params["pais"] = pais.strip()

    if puerto:
        filtros.append("puerto = %(puerto)s")
        params["puerto"] = puerto.strip()

    if surveyor:
        filtros.append("surveyor ILIKE %(surveyor)s")
        params["surveyor"] = f"%{surveyor.strip()}%"

    if estados:
        # ✅ Case-insensitive contra DB
        estados_norm = []
        for e in estados:
            if e is None:
                continue
            e2 = str(e).strip()
            if e2:
                estados_norm.append(e2.upper())

        if estados_norm:
            filtros.append("UPPER(estado) = ANY(%(estados)s)")
            params["estados"] = estados_norm

    if fecha_desde:
        filtros.append("fecha_inicio::date >= %(fecha_desde)s::date")
        params["fecha_desde"] = fecha_desde.strip()

    if fecha_hasta:
        filtros.append("fecha_inicio::date <= %(fecha_hasta)s::date")
        params["fecha_hasta"] = fecha_hasta.strip()

    if not filtros:
        # Si por alguna razón todo venía vacío tras normalizar → no consultamos
        cur.close()
        return []

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
