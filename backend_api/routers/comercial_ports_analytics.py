# ============================================================
# ROUTER — COMERCIAL / ANALYTICS / PUERTOS
# ============================================================

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
# RBAC GUARD (MISMO PATRÓN QUE CLIENT VIEW)
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
# GET /comercial/analytics/puertos/kpis
# ============================================================
@router.get(
    "/analytics/puertos/kpis",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_ports_kpis(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    clientes: Optional[List[str]] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = ["s.fecha_inicio IS NOT NULL"]
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    if continente:
        filtros.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("s.pais = %(pais)s")
        params["pais"] = pais

    if clientes:
        filtros.append("s.cliente = ANY(%(clientes)s)")
        params["clientes"] = clientes

    where_sql = " AND ".join(filtros)

    sql = f"""
        SELECT
            COUNT(DISTINCT s.cliente)                        AS clientes,
            COUNT(DISTINCT s.pais)                           AS paises,
            COUNT(DISTINCT s.puerto)                         AS puertos,

            SUM(
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN s.valor_factura / 1.13
                    ELSE s.valor_factura
                END
            )                                                AS facturacion_neta,

            SUM(COALESCE(s.honorarios,0))                    AS honorarios,
            SUM(COALESCE(s.costo_operativo,0))               AS costos_operativos

        FROM servicios s
        WHERE {where_sql};
    """

    cur.execute(sql, params)
    r = cur.fetchone()
    cur.close()

    fact = float(r["facturacion_neta"] or 0)
    honorarios = float(r["honorarios"] or 0)
    costos_op = float(r["costos_operativos"] or 0)

    margen_bruto = fact - honorarios
    margen_neto = fact - (honorarios + costos_op)

    return {
        "clientes": r["clientes"],
        "paises": r["paises"],
        "puertos": r["puertos"],
        "facturacion": round(fact, 2),
        "costos": round(honorarios + costos_op, 2),
        "margen_bruto": round(margen_bruto, 2),
        "margen_neto": round(margen_neto, 2),
        "rentabilidad": round(margen_neto, 2),
        "rentabilidad_pct": round((margen_neto / fact * 100) if fact else 0, 2)
    }


# ============================================================
# GET /comercial/analytics/puertos
# ============================================================
@router.get(
    "/analytics/puertos",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_ports_analytics(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    clientes: Optional[List[str]] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    filtros = ["s.fecha_inicio IS NOT NULL"]
    params = {}

    if year_from:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) >= %(year_from)s")
        params["year_from"] = year_from

    if year_to:
        filtros.append("EXTRACT(YEAR FROM s.fecha_inicio) <= %(year_to)s")
        params["year_to"] = year_to

    if continente:
        filtros.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("s.pais = %(pais)s")
        params["pais"] = pais

    if clientes:
        filtros.append("s.cliente = ANY(%(clientes)s)")
        params["clientes"] = clientes

    where_sql = " AND ".join(filtros)

    sql = f"""
        WITH base AS (
            SELECT
                s.continente,
                s.pais,
                s.puerto,
                CASE
                    WHEN s.pais = 'Costa Rica'
                    THEN s.valor_factura / 1.13
                    ELSE s.valor_factura
                END AS facturacion_neta,
                COALESCE(s.honorarios,0) AS honorarios,
                COALESCE(s.costo_operativo,0) AS costo_operativo
            FROM servicios s
            WHERE {where_sql}
        ),
        agg AS (
            SELECT
                continente,
                pais,
                puerto,
                COUNT(*) AS total_operaciones,
                SUM(facturacion_neta) AS facturacion_neta,
                SUM(honorarios) AS honorarios,
                SUM(costo_operativo) AS costo_operativo
            FROM base
            GROUP BY continente, pais, puerto
        ),
        ranked AS (
            SELECT *,
                SUM(facturacion_neta) OVER () AS total_global,
                SUM(facturacion_neta) OVER (ORDER BY facturacion_neta DESC) AS acumulado
            FROM agg
        )
        SELECT
            continente,
            pais,
            puerto,
            total_operaciones,
            ROUND(
                total_operaciones::numeric
                / NULLIF(SUM(total_operaciones) OVER (PARTITION BY pais), 0),
                2
            ) AS frecuencia,
            ROUND(facturacion_neta, 2) AS facturacion_neta,
            ROUND(
                facturacion_neta / NULLIF(total_operaciones,0),
                2
            ) AS ticket_promedio,
            ROUND(
                facturacion_neta - honorarios,
                2
            ) AS margen_bruto,
            ROUND(
                facturacion_neta - (honorarios + costo_operativo),
                2
            ) AS margen_neto,
            (acumulado / total_global <= 0.8) AS is_pareto_80
        FROM ranked
        ORDER BY facturacion_neta DESC;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return {"data": rows}


@router.get(
    "/analytics/puertos/filtros",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_ports_filters(conn=Depends(get_db)):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        WHERE fecha_inicio IS NOT NULL
        ORDER BY year DESC;
    """)
    years = [r["year"] for r in cur.fetchall()]

    cur.execute("""
        SELECT DISTINCT cliente
        FROM servicios
        WHERE cliente IS NOT NULL
        ORDER BY cliente;
    """)
    clientes = [r["cliente"] for r in cur.fetchall()]

    cur.close()

    return {
        "years": years,
        "clientes": clientes
    }
