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
        filtros.append("c.nombrejuridico = ANY(%(clientes)s)")
        params["clientes"] = clientes

    where_sql = " AND ".join(filtros)

    sql = f"""
        WITH base AS (
            SELECT
                s.cliente,
                s.pais AS servicio_pais,
                s.puerto,
                s.valor_factura,
                s.honorarios,
                s.costo_operativo,
                ca.comision,
                cli.pais AS cliente_pais
            FROM servicios s
            LEFT JOIN cliente cli
                ON cli.nombrejuridico = s.cliente
            LEFT JOIN cash_app ca
                ON ca.numero_documento = s.factura
            WHERE {where_sql}
        )
        SELECT
            COUNT(DISTINCT cliente)               AS clientes,
            COUNT(DISTINCT servicio_pais)         AS paises,
            COUNT(DISTINCT puerto)                AS puertos,

            SUM(
                CASE
                    WHEN cliente_pais = 'Costa Rica'
                    THEN valor_factura / 1.13
                    ELSE valor_factura
                END
            )                                     AS facturacion_neta,

            SUM(
                COALESCE(honorarios,0)
              + COALESCE(costo_operativo,0)
              + COALESCE(comision,0)
            )                                     AS costos

        FROM base;
    """

    cur.execute(sql, params)
    r = cur.fetchone()
    cur.close()

    fact = float(r["facturacion_neta"] or 0)
    costos = float(r["costos"] or 0)
    margen = fact - costos
    rent_pct = (margen / fact * 100) if fact else 0

    return {
        "clientes": r["clientes"],
        "paises": r["paises"],
        "puertos": r["puertos"],
        "facturacion": round(fact, 2),
        "costos": round(costos, 2),
        "margen_neto": round(margen, 2),
        "rentabilidad": round(margen, 2),
        "rentabilidad_pct": round(rent_pct, 2)
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
        filtros.append("c.nombrejuridico = ANY(%(clientes)s)")
        params["clientes"] = clientes

    where_sql = " AND ".join(filtros)

    sql = f"""
        WITH base AS (
            SELECT
                s.continente,
                s.pais,
                s.puerto,
                s.valor_factura,
                cli.pais AS cliente_pais
            FROM servicios s
            LEFT JOIN cliente cli
                ON cli.nombrejuridico = s.cliente
            WHERE {where_sql}
        ),
        agg AS (
            SELECT
                continente,
                pais,
                puerto,
                COUNT(*) AS total_operaciones,
                SUM(
                    CASE
                        WHEN cliente_pais = 'Costa Rica'
                        THEN valor_factura / 1.13
                        ELSE valor_factura
                    END
                ) AS facturacion_neta
            FROM base
            GROUP BY continente, pais, puerto
        ),
        ranked AS (
            SELECT *,
                SUM(facturacion_neta) OVER () AS total_global,
                SUM(facturacion_neta) OVER (
                    ORDER BY facturacion_neta DESC
                ) AS acumulado
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
            (acumulado / total_global <= 0.8) AS is_pareto_80
        FROM ranked
        ORDER BY facturacion_neta DESC;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return {
        "data": rows
    }
