# ============================================================
# ROUTER — COMERCIAL / ANALYTICS / PUERTOS
# ============================================================

from fastapi import APIRouter, Depends, Query
from psycopg2.extras import RealDictCursor
from typing import Optional, List
from database import get_db
from auth import get_current_user

router = APIRouter(
    prefix="/comercial/analytics/puertos",
    tags=["Comercial Analytics"]
)

# ============================================================
# GET — PORT PERFORMANCE ANALYTICS
# ============================================================
@router.get("")
def get_ports_analytics(
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    clientes: Optional[List[str]] = Query(None),
    continente: Optional[str] = Query(None),
    pais: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # =====================================================
    # 1️⃣ AÑOS DISPONIBLES
    # =====================================================
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        WHERE fecha_inicio IS NOT NULL
        ORDER BY year;
    """)
    years_available = [r["year"] for r in cur.fetchall()]

    if not years_available:
        return {"years_available": [], "data": []}

    year_from = year_from or min(years_available)
    year_to = year_to or max(years_available)

    # =====================================================
    # 2️⃣ FILTROS DINÁMICOS
    # =====================================================
    filters = [
        "s.fecha_inicio IS NOT NULL",
        "EXTRACT(YEAR FROM s.fecha_inicio) BETWEEN %(year_from)s AND %(year_to)s"
    ]

    params = {
        "year_from": year_from,
        "year_to": year_to
    }

    if continente:
        filters.append("s.continente = %(continente)s")
        params["continente"] = continente

    if pais:
        filters.append("s.pais = %(pais)s")
        params["pais"] = pais

    if clientes:
        filters.append("c.nombrejuridico = ANY(%(clientes)s)")
        params["clientes"] = clientes

    where_clause = " AND ".join(filters)

    # =====================================================
    # 3️⃣ QUERY PRINCIPAL
    # =====================================================
    sql = f"""
        WITH base AS (
            SELECT
                s.continente,
                s.pais,
                s.puerto,
                s.valor_factura,
                s.honorarios,
                s.costo_operativo,
                c.pais AS cliente_pais
            FROM servicios s
            LEFT JOIN clientes c ON c.nombrejuridico = s.cliente
            WHERE {where_clause}
        ),
        calc AS (
            SELECT
                continente,
                pais,
                puerto,

                COUNT(*) AS total_operaciones,
                COUNT(valor_factura) AS operaciones_facturadas,

                SUM(valor_factura) AS facturacion_bruta,

                SUM(
                    CASE
                        WHEN valor_factura IS NULL THEN 0
                        WHEN cliente_pais = 'Costa Rica'
                            THEN valor_factura / 1.13
                        ELSE valor_factura
                    END
                ) AS facturacion_neta,

                SUM(
                    CASE
                        WHEN valor_factura IS NULL THEN 0
                        WHEN cliente_pais = 'Costa Rica'
                            THEN valor_factura - (valor_factura / 1.13)
                        ELSE 0
                    END
                ) AS iva_total,

                SUM(COALESCE(honorarios,0) + COALESCE(costo_operativo,0)) AS costo_total
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
                END AS margen_bruto_pct,
                SUM(facturacion_neta) OVER (PARTITION BY continente ORDER BY facturacion_neta DESC)
                    /
                NULLIF(SUM(facturacion_neta) OVER (PARTITION BY continente),0) AS acumulado_pct
            FROM calc
        )
        SELECT
            continente,
            pais,
            puerto,
            total_operaciones,
            operaciones_facturadas,
            ROUND(total_operaciones::numeric / NULLIF(%(period)s,0), 2) AS frecuencia,
            ROUND(facturacion_bruta,2) AS facturacion_bruta,
            ROUND(facturacion_neta,2) AS facturacion_neta,
            ROUND(iva_total,2) AS iva_total,
            ROUND(
                CASE
                    WHEN operaciones_facturadas > 0
                        THEN facturacion_neta / operaciones_facturadas
                    ELSE 0
                END, 2
            ) AS ticket_promedio,
            ROUND(costo_total,2) AS costo_total,
            ROUND(margen_bruto,2) AS margen_bruto,
            ROUND(margen_bruto_pct,2) AS margen_bruto_pct,
            (acumulado_pct <= 0.8) AS is_pareto_80
        FROM ranked
        ORDER BY continente, facturacion_neta DESC;
    """

    params["period"] = (year_to - year_from + 1) * 12

    cur.execute(sql, params)
    data = cur.fetchall()

    return {
        "years_available": years_available,
        "data": data
    }
