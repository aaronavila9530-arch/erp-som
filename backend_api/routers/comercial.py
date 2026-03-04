from fastapi import (
    APIRouter,
    Query,
    Header,
    HTTPException,
    Depends
)
from typing import Optional, List
from psycopg2.extras import RealDictCursor
from datetime import date

from database import get_db
from rbac_service import has_permission


router = APIRouter(
    prefix="/comercial",
    tags=["Comercial"]
)

# ============================================================
# RBAC GUARD
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
    year: Optional[int] = Query(None),   # 👈 NUEVO FILTRO DE AÑO
    conn=Depends(get_db)
):
    """
    Reglas:
    - Confirmado / Buque por confirmar → SOLO año en curso
    - Finalizado → todos los años (o year si viene)
    """

    # ----------------------------
    # Normalizar strings
    # ----------------------------
    cliente = cliente.strip() if cliente else None
    continente = continente.strip() if continente else None
    pais = pais.strip() if pais else None
    puerto = puerto.strip() if puerto else None
    surveyor = surveyor.strip() if surveyor else None

    if estados:
        estados = [e.strip() for e in estados if e and e.strip()]
        if not estados:
            estados = None

    if not any([cliente, continente, pais, puerto, surveyor, estados, year]):
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    # ----------------------------
    # Filtros básicos
    # ----------------------------
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

    # ----------------------------
    # Estados
    # ----------------------------
    estados_confirmacion = {"Confirmado", "Buque por confirmar"}
    estados_finalizado = {"FINALIZADO"}

    if estados:
        filtros.append("estado = ANY(%(estados)s)")
        params["estados"] = estados

        # 👉 Regla año automático SOLO para confirmación
        if any(e in estados_confirmacion for e in estados):
            current_year = date.today().year
            params["y_start"] = f"{current_year}-01-01"
            params["y_end"] = f"{current_year + 1}-01-01"
            filtros.append(
                "fecha_inicio >= %(y_start)s AND fecha_inicio < %(y_end)s"
            )

    # ----------------------------
    # Filtro de año EXPLÍCITO
    # (solo aplica si viene year)
    # ----------------------------
    if year:
        params["year_start"] = f"{year}-01-01"
        params["year_end"] = f"{year + 1}-01-01"
        filtros.append(
            "fecha_inicio >= %(year_start)s AND fecha_inicio < %(year_end)s"
        )

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
        LIMIT 500000
    """

    cur.execute(sql, params)
    data = cur.fetchall()
    cur.close()

    return data
