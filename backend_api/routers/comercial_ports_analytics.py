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
# GET /comercial/analytics/puertos
# ANALÍTICA COMERCIAL POR PUERTO
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

    # --------------------------------------------------------
    # AÑOS DISPONIBLES
    # --------------------------------------------------------
    cur.execute("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        WHERE fecha_inicio IS NOT NULL
        ORDER BY year;
    """)
    years_available = [r["year"] for r in cur.fetchall()]

    if not years_available:
        cur.close()
        return {
            "years_available": [],
            "data": []
        }

    year_from = year_from or min(years_available)
    year_to = year_to or max(years_available)

    # --------------------------------------------------------
    # FILTROS DINÁMICOS
    # --------------------------------------------------------
    filtros = [
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    if continente:
        filtros.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filtros.append("s.pais = %(pais)s")
        params["pais"] = pais

    if clientes:
        filtros.append("c.nombrejuridico = ANY(%(clientes)s)")
        params["clientes"] = clientes

    filtros_sql = " AND ".join(filtros)

    # --------------------------------------------------------
    # SQL PRINCIPAL (ALINEADO A CLIENT VIEW)
    # --------------------------------------------------------
    sql = f"""
        WITH base AS (
            SELECT
                s.continente,
                s.pais,
                s.puerto,
                COALESCE(s.valor_factura, 0)     AS valor_factura,
                COALESCE(s.honorarios, 0)        AS honorarios,
                COALESCE(s.costo_operativo, 0)   AS costo_operativo,
                cli.pais                         AS cliente_pais
            FROM servicios s
            LEFT JOIN cliente cli
                ON cli.nombrejuridico = s.cliente
            WHERE {filtros_sql}
        ),
        calc AS (
            SELECT
                continente,
                pais,
                puerto,
                COUNT(*)                         AS total_operaciones,
                COUNT(valor_factura)             AS operaciones_facturadas,
                SUM(valor_factura)               AS facturacion_bruta,
                SUM(
                    CASE
                        WHEN cliente_pais = 'Costa Rica'
                        THEN valor_factura / 1.13
                        ELSE valor_factura
                    END
                )                                AS facturacion_neta,
                SUM(
                    CASE
                        WHEN cliente_pais = 'Costa Rica'
                        THEN valor_factura - (valor_factura / 1.13)
                        ELSE 0
                    END
                )                                AS iva_total,
                SUM(honorarios + costo_operativo) AS costo_total
            FROM base
            GROUP BY continente, pais, puerto
        ),
        ranked AS (
            SELECT *,
                (facturacion_neta - costo_total) AS margen_bruto,
                CASE
                    WHEN facturacion_neta > 0
                    THEN ((facturacion_neta - costo_total) / facturacion_neta) * 100
                    ELSE 0
                END                              AS margen_bruto_pct,
                SUM(facturacion_neta) OVER (
                    PARTITION BY continente
                    ORDER BY facturacion_neta DESC
                )
                /
                NULLIF(
                    SUM(facturacion_neta) OVER (PARTITION BY continente),
                    0
                )                                AS acumulado_pct
            FROM calc
        )
        SELECT
            continente,
            pais,
            puerto,
            total_operaciones,
            operaciones_facturadas,
            ROUND(
                total_operaciones::numeric
                / NULLIF(%(period)s, 0),
                2
            )                                   AS frecuencia,
            ROUND(facturacion_bruta, 2)         AS facturacion_bruta,
            ROUND(facturacion_neta, 2)          AS facturacion_neta,
            ROUND(iva_total, 2)                 AS iva_total,
            ROUND(
                CASE
                    WHEN operaciones_facturadas > 0
                    THEN facturacion_neta / operaciones_facturadas
                    ELSE 0
                END,
                2
            )                                   AS ticket_promedio,
            ROUND(costo_total, 2)               AS costo_total,
            ROUND(margen_bruto, 2)              AS margen_bruto,
            ROUND(margen_bruto_pct, 2)          AS margen_bruto_pct,
            (acumulado_pct <= 0.8)              AS is_pareto_80
        FROM ranked
        ORDER BY continente, facturacion_neta DESC;
    """

    params["period"] = (year_to - year_from + 1) * 12

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()

    return {
        "years_available": years_available,
        "data": rows
    }
