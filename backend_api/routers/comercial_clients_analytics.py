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
# GET /comercial/client-view
# ANALÍTICA COMERCIAL POR CLIENTE
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
    KPIs por cliente basados en servicios.

    Reglas:
    - Por defecto: año en curso (fecha_inicio)
    - Si year viene → usa ese año
    - IVA:
        • Costa Rica → valor_factura / 1.13
        • Otros países → valor_factura completo
    - Comisión bancaria:
        • Desde cash_app.comision
        • Match por numero_documento = servicios.factura
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
    # QUERY PRINCIPAL
    # --------------------------------------------------------
    sql = """
        WITH servicios_base AS (
            SELECT
                s.cliente,
                COUNT(*)                           AS total_servicios,
                SUM(s.valor_factura)               AS total_facturado,
                SUM(s.honorarios)                  AS total_honorarios,
                SUM(s.costo_operativo)             AS total_costo_operativo,
                SUM(
                    COALESCE(ca.comision, 0)
                )                                  AS total_comision_bancaria,
                SUM(
                    CASE
                        WHEN cli.pais = 'Costa Rica'
                        THEN s.valor_factura / 1.13
                        ELSE s.valor_factura
                    END
                )                                  AS subtotal,
                SUM(
                    CASE
                        WHEN cli.pais = 'Costa Rica'
                        THEN s.valor_factura - (s.valor_factura / 1.13)
                        ELSE 0
                    END
                )                                  AS iva
            FROM servicios s
            LEFT JOIN clientes cli
                ON cli.nombrejuridico = s.cliente
            LEFT JOIN cash_app ca
                ON ca.numero_documento = s.factura
            WHERE
                s.fecha_inicio >= %(y_start)s
                AND s.fecha_inicio < %(y_end)s
            GROUP BY
                s.cliente
        )
        SELECT
            cliente,
            total_servicios,
            total_facturado,
            subtotal,
            iva,
            total_honorarios,
            total_costo_operativo,
            total_comision_bancaria,
            (
                total_facturado
                - total_costo_operativo
                - total_honorarios
            ) AS margen_bruto,
            (
                total_facturado
                - total_costo_operativo
                - total_honorarios
                - total_comision_bancaria
                - iva
            ) AS margen_neto
        FROM servicios_base
        ORDER BY total_facturado DESC;
    """

    cur.execute(sql, {
        "y_start": y_start,
        "y_end": y_end
    })

    data = cur.fetchall()

    # --------------------------------------------------------
    # AÑOS DISPONIBLES (PARA FILTRO UI)
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
        "data": data
    }
