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
    year: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    Reglas operativas ERP-SOM:

    Confirmado / Buque por confirmar
        → SOLO año actual automáticamente

    Finalizado
        → Todos los años (o el año indicado)

    Cancelado
        → Todos los años (o el año indicado)
    """

    # ---------------------------------------------------------
    # NORMALIZACIÓN SEGURA DE STRINGS
    # ---------------------------------------------------------
    cliente = cliente.strip() if cliente and cliente.strip() else None
    continente = continente.strip() if continente and continente.strip() else None
    pais = pais.strip() if pais and pais.strip() else None
    puerto = puerto.strip() if puerto and puerto.strip() else None
    surveyor = surveyor.strip() if surveyor and surveyor.strip() else None

    # ---------------------------------------------------------
    # NORMALIZAR ESTADOS
    # ---------------------------------------------------------
    if estados:
        estados = [
            e.strip().lower()
            for e in estados
            if e and e.strip()
        ]

        if not estados:
            estados = None

    # ---------------------------------------------------------
    # PROTECCIÓN CONTRA CONSULTA VACÍA
    # (evita traer toda la tabla accidentalmente)
    # ---------------------------------------------------------
    if not any([cliente, continente, pais, puerto, surveyor, estados, year]):
        return []

    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = []
    params = {}

    # ---------------------------------------------------------
    # FILTROS BÁSICOS
    # ---------------------------------------------------------
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

    # ---------------------------------------------------------
    # ESTADOS
    # ---------------------------------------------------------
    estados_confirmacion = {"confirmado", "buque por confirmar"}

    if estados:

        filtros.append("LOWER(estado) = ANY(%(estados)s)")
        params["estados"] = estados

        # -----------------------------------------------------
        # REGLA: estados operativos → SOLO año actual
        # -----------------------------------------------------
        if any(e in estados_confirmacion for e in estados):

            current_year = date.today().year

            params["y_start"] = f"{current_year}-01-01"
            params["y_end"] = f"{current_year + 1}-01-01"

            filtros.append(
                "fecha_inicio >= %(y_start)s AND fecha_inicio < %(y_end)s"
            )

    # ---------------------------------------------------------
    # FILTRO EXPLÍCITO POR AÑO
    # ---------------------------------------------------------
    if year:

        params["year_start"] = f"{year}-01-01"
        params["year_end"] = f"{year + 1}-01-01"

        filtros.append(
            "fecha_inicio >= %(year_start)s AND fecha_inicio < %(year_end)s"
        )

    # ---------------------------------------------------------
    # SQL WHERE
    # ---------------------------------------------------------
    where_sql = " AND ".join(filtros) if filtros else "TRUE"

    # ---------------------------------------------------------
    # QUERY FINAL
    # ---------------------------------------------------------
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

    try:

        cur.execute(sql, params)
        data = cur.fetchall()

        return data

    finally:
        cur.close()
