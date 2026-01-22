from fastapi import (
    APIRouter,
    Query,
    Header,
    HTTPException,
    Depends
)
from typing import Optional
from psycopg2.extras import RealDictCursor
from datetime import date, datetime

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
            raise HTTPException(status_code=403, detail="No autorizado")
    return checker


# ============================================================
# GET /comercial/client-view
# ANALÍTICA COMERCIAL POR CLIENTE / BUQUE / SERVICIO
# ============================================================
@router.get(
    "/client-view",
    dependencies=[Depends(require_permission("comercial", "view"))]
)
def comercial_client_view(
    year: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    cliente: Optional[str] = Query(None),
    servicio: Optional[str] = Query(None),
    conn=Depends(get_db)
):
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # --------------------------------------------------------
    # RANGO DE FECHAS EFECTIVO
    # --------------------------------------------------------
    if date_from and date_to:
        f_start = date_from
        f_end = date_to
    else:
        y = year or date.today().year
        f_start = date(y, 1, 1)
        f_end = date(y + 1, 1, 1)

    # --------------------------------------------------------
    # SQL BASE
    # --------------------------------------------------------
    sql = """
        WITH base AS (
            SELECT
                s.cliente,
                s.operacion                       AS servicio,
                s.buque_contenedor               AS buque,
                s.fecha_inicio,
                s.fecha_fin,
                COALESCE(s.valor_factura, 0)     AS valor_factura,
                COALESCE(s.costo_operativo, 0)   AS costo_operativo,
                COALESCE(s.honorarios, 0)        AS honorarios,
                cli.pais,
                COALESCE(ca.comision, 0)         AS comision_bancaria,
                CASE
                    WHEN cli.pais = 'Costa Rica'
                    THEN COALESCE(s.valor_factura, 0) - (COALESCE(s.valor_factura, 0) / 1.13)
                    ELSE 0
                END                               AS iva
            FROM servicios s
            LEFT JOIN clientes cli
                ON cli.nombrejuridico = s.cliente
            LEFT JOIN cash_app ca
                ON ca.numero_documento = s.factura
            WHERE
                s.fecha_inicio >= %(f_start)s
                AND s.fecha_inicio < %(f_end)s
    """

    params = {
        "f_start": f_start,
        "f_end": f_end
    }

    if cliente:
        sql += " AND s.cliente = %(cliente)s"
        params["cliente"] = cliente

    if servicio:
        sql += " AND s.operacion = %(servicio)s"
        params["servicio"] = servicio

    sql += """
        )
        SELECT
            cliente,
            buque,
            servicio,
            COUNT(*)                         AS frecuencia,
            MIN(fecha_inicio)                AS fecha_inicio,
            MAX(fecha_fin)                   AS fecha_fin,
            SUM(valor_factura)               AS valor_facturado,
            SUM(costo_operativo)             AS costo_operativo,
            SUM(honorarios)                  AS honorarios,
            SUM(iva)                         AS iva,
            SUM(comision_bancaria)           AS comision_bancaria,
            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
            )                                AS margen_bruto,
            (
                SUM(valor_factura)
                - SUM(costo_operativo)
                - SUM(honorarios)
                - SUM(iva)
                - SUM(comision_bancaria)
            )                                AS margen_neto
        FROM base
        GROUP BY
            cliente,
            buque,
            servicio
        ORDER BY valor_facturado DESC;
    """

    cur.execute(sql, params)
    rows = cur.fetchall()

    # --------------------------------------------------------
    # KPIs (YA FILTRADOS)
    # --------------------------------------------------------
    total_clients = len({r["cliente"] for r in rows if r["cliente"]})
    total_services = sum(r["frecuencia"] or 0 for r in rows)
    total_fact = sum(r["valor_facturado"] or 0 for r in rows)
    total_costs = sum(
        (r["costo_operativo"] or 0)
        + (r["honorarios"] or 0)
        + (r["iva"] or 0)
        + (r["comision_bancaria"] or 0)
        for r in rows
    )
    net_margin = sum(r["margen_neto"] or 0 for r in rows)
    gross_margin = sum(r["margen_bruto"] or 0 for r in rows)

    kpis = {
        "clientes": total_clients,
        "servicios": total_services,
        "facturado": round(total_fact, 2),
        "costos": round(total_costs, 2),
        "ticket_promedio": round(
            total_fact / total_services, 2
        ) if total_services else 0,
        "margen_bruto": round(gross_margin, 2),
        "margen_neto": round(net_margin, 2),
        "rentabilidad_monto": round(net_margin, 2),
        "rentabilidad_pct": round(
            (net_margin / total_fact) * 100, 2
        ) if total_fact else 0
    }

    # --------------------------------------------------------
    # AÑOS DISPONIBLES
    # --------------------------------------------------------
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM fecha_inicio)::int AS year
        FROM servicios
        ORDER BY year DESC
    """)
    years = [r["year"] for r in cur.fetchall()]

    cur.close()

    return {
        "date_from": f_start,
        "date_to": f_end,
        "available_years": years,
        "kpis": kpis,
        "data": rows
    }
