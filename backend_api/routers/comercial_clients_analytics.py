from fastapi import (
    APIRouter,
    Query,
    Header,
    HTTPException,
    Depends
)
from typing import Optional
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
# GET /comercial/client-view
# ANALÍTICA COMERCIAL POR CLIENTE / SERVICIO
# ============================================================
@router.get(
    "/client-view",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_client_view(
    year: Optional[int] = Query(None),
    conn=Depends(get_db)
):
    """
    Analítica comercial basada en tabla servicios.

    Reglas:
    - Año por defecto: año actual (fecha_inicio)
    - IVA:
        • Costa Rica  → valor_factura / 1.13
        • Otros       → valor_factura completo
    - Comisión bancaria:
        • cash_app.comision
        • Match: numero_documento = servicios.factura
    - KPIs calculados en backend
    """

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # AÑO EFECTIVO
    # --------------------------------------------------------
    if year:
        y_start = date(year, 1, 1)
        y_end = date(year + 1, 1, 1)
    else:
        current_year = date.today().year
        y_start = date(current_year, 1, 1)
        y_end = date(current_year + 1, 1, 1)

    # --------------------------------------------------------
    # DATA BASE (SERVICIOS)
    # --------------------------------------------------------
    sql = """
        WITH base AS (
            SELECT
                s.cliente,
                s.operacion                            AS servicios,
                s.operacion                            AS tipo_mas_frecuente,
                s.fecha_inicio,
                s.fecha_fin,
                s.factura,
                s.valor_factura,
                s.costo_operativo,
                s.honorarios,
                cli.pais,
                COALESCE(ca.comision, 0)              AS comision_bancaria,
                CASE
                    WHEN cli.pais = 'Costa Rica'
                    THEN s.valor_factura - (s.valor_factura / 1.13)
                    ELSE 0
                END                                    AS iva,
                CASE
                    WHEN cli.pais = 'Costa Rica'
                    THEN s.valor_factura / 1.13
                    ELSE s.valor_factura
                END                                    AS subtotal
            FROM servicios s
            LEFT JOIN clientes cli
                ON cli.nombrejuridico = s.cliente
            LEFT JOIN cash_app ca
                ON ca.numero_documento = s.factura
            WHERE
                s.fecha_inicio >= %(y_start)s
                AND s.fecha_inicio < %(y_end)s
        )
        SELECT
            cliente,
            servicios,
            COUNT(*)                                 AS frecuencia,
            tipo_mas_frecuente,
            MIN(fecha_inicio)                        AS fecha_inicio,
            MAX(fecha_fin)                           AS fecha_fin,
            factura,
            SUM(valor_factura)                       AS valor_facturado,
            SUM(costo_operativo)                     AS costo_operativo,
            SUM(honorarios)                          AS honorarios,
            SUM(iva)                                 AS iva,
            SUM(comision_bancaria)                   AS comision_bancaria,
            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
            )                                        AS margen_bruto,
            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
                - SUM(comision_bancaria)
                - SUM(iva)
            )                                        AS margen_neto
        FROM base
        GROUP BY
            cliente,
            servicios,
            tipo_mas_frecuente,
            factura
        ORDER BY valor_facturado DESC;
    """

    cur.execute(sql, {
        "y_start": y_start,
        "y_end": y_end
    })

    rows = cur.fetchall()

    # --------------------------------------------------------
    # KPIs (BACKEND)
    # --------------------------------------------------------
    total_clients = len({r["cliente"] for r in rows if r["cliente"]})
    total_services = sum(r["frecuencia"] for r in rows)
    total_fact = sum(r["valor_facturado"] or 0 for r in rows)
    total_costs = sum(
        (r["costo_operativo"] or 0)
        + (r["honorarios"] or 0)
        + (r["iva"] or 0)
        + (r["comision_bancaria"] or 0)
        for r in rows
    )
    gross_margin = sum(r["margen_bruto"] or 0 for r in rows)
    net_margin = sum(r["margen_neto"] or 0 for r in rows)

    kpis = {
        "kpi_clients": total_clients,
        "kpi_services": total_services,
        "kpi_revenue": round(total_fact, 2),
        "kpi_costs": round(total_costs, 2),
        "kpi_ticket_avg": round(
            (total_fact / total_services), 2
        ) if total_services else 0,
        "kpi_gross_margin": round(gross_margin, 2),
        "kpi_net_margin": round(net_margin, 2),
        "kpi_profit_amt": round(net_margin, 2),
        "kpi_profit_pct": round(
            (net_margin / total_fact) * 100, 2
        ) if total_fact else 0
    }

    # --------------------------------------------------------
    # AÑOS DISPONIBLES
    # --------------------------------------------------------
    cur.execute("""
        SELECT DISTINCT
            EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        ORDER BY year DESC
    """)
    years = [r["year"] for r in cur.fetchall()]

    cur.close()

    return {
        "year_applied": year or date.today().year,
        "available_years": years,
        "kpis": kpis,
        "data": rows
    }
